from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class Empresa(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    cnpj = models.CharField("CNPJ", max_length=18, blank=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Filial(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="filiais")
    nome = models.CharField(max_length=120)
    cidade = models.CharField(max_length=120, blank=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "filiais"
        ordering = ["empresa__nome", "nome"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "nome"], name="filial_unica_por_empresa"),
        ]

    def __str__(self):
        return f"{self.empresa} - {self.nome}"


class Usuario(AbstractUser):
    """Usuário do sistema. O papel define o que ele enxerga."""

    class Papel(models.TextChoices):
        ADMIN_GRUPO = "admin_grupo", "Administrador do grupo"
        GESTOR_EMPRESA = "gestor_empresa", "Gestor de empresa"
        GESTOR_FILIAL = "gestor_filial", "Gestor de filial"
        COLABORADOR = "colaborador", "Colaborador"

    papel = models.CharField(max_length=20, choices=Papel.choices, default=Papel.COLABORADOR)
    empresa = models.ForeignKey(
        Empresa, on_delete=models.PROTECT, null=True, blank=True, related_name="usuarios"
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.PROTECT, null=True, blank=True, related_name="usuarios"
    )

    def clean(self):
        super().clean()
        if self.papel == self.Papel.ADMIN_GRUPO:
            return
        if not self.empresa:
            raise ValidationError({"empresa": "Informe a empresa deste usuário."})
        if self.papel in (self.Papel.GESTOR_FILIAL, self.Papel.COLABORADOR) and not self.filial:
            raise ValidationError({"filial": "Informe a filial deste usuário."})
        if self.filial and self.filial.empresa_id != self.empresa_id:
            raise ValidationError({"filial": "A filial precisa ser da empresa escolhida."})

    @property
    def ve_grupo_todo(self):
        return self.is_superuser or self.papel == self.Papel.ADMIN_GRUPO

    def has_perm(self, perm, obj=None):
        # O administrador do grupo (com acesso a Cadastros) gerencia tudo, como um superusuário.
        if self.is_active and self.is_staff and self.papel == self.Papel.ADMIN_GRUPO:
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if self.is_active and self.is_staff and self.papel == self.Papel.ADMIN_GRUPO:
            return True
        return super().has_module_perms(app_label)

    @property
    def gerencia_usuarios(self):
        """Só o administrador do grupo (TI) cadastra logins e senhas."""
        return self.ve_grupo_todo

    def usuarios_gerenciaveis(self):
        """Usuários que esta pessoa pode ver e editar na tela Usuários (nunca ela mesma)."""
        if not self.gerencia_usuarios:
            return Usuario.objects.none()
        qs = Usuario.objects.exclude(pk=self.pk)
        if not self.is_superuser:
            qs = qs.exclude(is_superuser=True)
        return qs

    def empresas_visiveis(self):
        if self.ve_grupo_todo:
            return Empresa.objects.all()
        return Empresa.objects.filter(pk=self.empresa_id)

    def filiais_visiveis(self):
        """Regra central de acesso: toda tela deve filtrar os dados por aqui."""
        if self.ve_grupo_todo:
            return Filial.objects.all()
        if self.papel == self.Papel.GESTOR_EMPRESA:
            return Filial.objects.filter(empresa_id=self.empresa_id)
        return Filial.objects.filter(pk=self.filial_id)


class TentativaLogin(models.Model):
    """Senha errada no login. Muitas seguidas bloqueiam o usuário por alguns minutos."""

    username = models.CharField(max_length=150, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "tentativa de login"
        verbose_name_plural = "tentativas de login"
