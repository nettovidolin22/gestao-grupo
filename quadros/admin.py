from django.contrib import admin

from .models import Coluna, Grupo, Item, Quadro


class GrupoInline(admin.TabularInline):
    model = Grupo
    extra = 0


class ColunaInline(admin.TabularInline):
    model = Coluna
    extra = 0


@admin.register(Quadro)
class QuadroAdmin(admin.ModelAdmin):
    list_display = ["nome", "filial", "arquivado", "criado_em"]
    list_filter = ["filial__empresa", "filial", "arquivado"]
    search_fields = ["nome"]
    inlines = [GrupoInline, ColunaInline]


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ["nome", "grupo", "criado_em"]
    search_fields = ["nome"]
