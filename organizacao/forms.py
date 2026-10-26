from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import TentativaLogin, Usuario


def ip_da_requisicao(request):
    if request is None:
        return None
    # Atrás do Render/Cloudflare o IP real vem no primeiro valor de X-Forwarded-For.
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = encaminhado.split(",")[0].strip() or request.META.get("REMOTE_ADDR")
    return ip or None


class LoginForm(AuthenticationForm):
    """Login que bloqueia o usuário depois de várias senhas erradas seguidas."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Usuário ou senha incorretos.",
        "inactive": "Usuário ou senha incorretos.",
        "bloqueado": "Muitas tentativas erradas. Espere %(minutos)s minutos e tente de novo.",
    }

    def clean(self):
        username = (self.cleaned_data.get("username") or "").strip().lower()
        if username:
            desde = timezone.now() - timedelta(seconds=settings.LOGIN_BLOQUEIO_SEGUNDOS)
            erros = TentativaLogin.objects.filter(username=username, criada_em__gte=desde).count()
            if erros >= settings.LOGIN_TENTATIVAS_MAXIMAS:
                raise ValidationError(
                    self.error_messages["bloqueado"],
                    code="bloqueado",
                    params={"minutos": settings.LOGIN_BLOQUEIO_SEGUNDOS // 60},
                )
        try:
            return super().clean()
        except ValidationError:
            if username:
                TentativaLogin.objects.create(username=username, ip=ip_da_requisicao(self.request))
                TentativaLogin.objects.filter(criada_em__lt=timezone.now() - timedelta(days=1)).delete()
            raise
        finally:
            if self.user_cache is not None and username:
                TentativaLogin.objects.filter(username=username).delete()


class UsuarioForm(forms.ModelForm):
    """Cadastro de usuário pela tela Usuários, limitado ao que o gestor pode conceder."""

    senha1 = forms.CharField(label="Senha inicial", widget=forms.PasswordInput, required=False,
                             help_text="Peça para a pessoa trocar no primeiro acesso.")
    senha2 = forms.CharField(label="Confirme a senha", widget=forms.PasswordInput, required=False)

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "username", "email", "papel", "empresa", "filial", "is_active"]
        labels = {"first_name": "Nome", "last_name": "Sobrenome", "username": "Usuário (para entrar)",
                  "email": "E-mail", "is_active": "Ativo"}
        help_texts = {"is_active": "Desmarque para bloquear o acesso sem perder o histórico.",
                      "username": "Sem espaços. Pode usar letras, números e . @ + - _"}

    def __init__(self, *args, gestor, **kwargs):
        super().__init__(*args, **kwargs)
        self.gestor = gestor
        papeis = gestor.papeis_que_pode_cadastrar()
        self.fields["papel"].choices = [(p.value, p.label) for p in papeis]
        self.fields["empresa"].queryset = gestor.empresas_visiveis()
        self.fields["filial"].queryset = gestor.filiais_visiveis().select_related("empresa")
        self.fields["empresa"].required = False
        self.fields["filial"].required = False
        # Gestores só cadastram na própria empresa (e o de filial, na própria filial).
        if not gestor.ve_grupo_todo:
            del self.fields["empresa"]
            self.instance.empresa = gestor.empresa
        if not gestor.ve_grupo_todo and gestor.papel == Usuario.Papel.GESTOR_FILIAL:
            del self.fields["filial"]
            self.instance.filial = gestor.filial
        if self.instance.pk:
            del self.fields["senha1"], self.fields["senha2"]
        else:
            self.fields["senha1"].required = True
            self.fields["senha2"].required = True
            self.fields["is_active"].initial = True

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        repetido = Usuario.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if repetido.exists():
            raise ValidationError("Já existe um usuário com esse nome.")
        return username

    def clean(self):
        dados = super().clean()
        if dados.get("papel") == Usuario.Papel.ADMIN_GRUPO:
            self.instance.empresa = self.instance.filial = None
            dados["empresa"] = dados["filial"] = None
        if "senha1" in self.fields:
            s1, s2 = dados.get("senha1"), dados.get("senha2")
            if s1 and s1 != s2:
                self.add_error("senha2", "As senhas não conferem.")
            elif s1:
                try:
                    password_validation.validate_password(s1, self.instance)
                except ValidationError as e:
                    self.add_error("senha1", e)
        return dados

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if "senha1" in self.fields:
            usuario.set_password(self.cleaned_data["senha1"])
        # Quem administra o grupo também precisa entrar em Cadastros.
        usuario.is_staff = usuario.is_superuser or usuario.papel == Usuario.Papel.ADMIN_GRUPO
        if commit:
            usuario.save()
        return usuario
