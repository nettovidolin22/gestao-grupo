from django.conf import settings
from django.db import models


class Notificacao(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificacoes"
    )
    texto = models.CharField(max_length=300)
    link = models.CharField(max_length=300, blank=True)
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "notificação"
        verbose_name_plural = "notificações"
        ordering = ["-criada_em"]
        indexes = [models.Index(fields=["usuario", "lida"])]

    def __str__(self):
        return self.texto
