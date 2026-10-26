from datetime import timedelta

from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import TentativaLogin


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
