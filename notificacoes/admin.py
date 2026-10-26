from django.contrib import admin

from .models import Notificacao


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ["texto", "usuario", "lida", "criada_em"]
    list_filter = ["lida"]
