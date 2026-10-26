import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notificacao

logger = logging.getLogger(__name__)


def notificar(usuario, texto, link="", autor=None, email=True):
    """Cria a notificação no sistema e, se o usuário tiver e-mail, avisa por e-mail.

    Ninguém é notificado das próprias ações.
    """
    if usuario is None or not usuario.is_active or (autor and usuario.pk == autor.pk):
        return None
    notificacao = Notificacao.objects.create(usuario=usuario, texto=texto[:300], link=link)
    if email and usuario.email:
        corpo = texto
        if link:
            corpo += f"\n\n{settings.SITE_URL.rstrip('/')}{link}"
        try:
            # Quebra de linha no assunto faz o Django recusar o e-mail.
            assunto = " ".join(texto[:80].split())
            send_mail(f"[Gestão do Grupo] {assunto}", corpo, None, [usuario.email])
        except Exception:
            # Falha de e-mail não pode impedir o trabalho no sistema.
            logger.exception("Falha ao enviar e-mail para %s", usuario.email)
    return notificacao
