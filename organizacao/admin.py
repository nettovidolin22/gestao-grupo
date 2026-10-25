from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Empresa, Filial, Usuario


class FilialInline(admin.TabularInline):
    model = Filial
    extra = 0


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ["nome", "cnpj", "ativa"]
    search_fields = ["nome", "cnpj"]
    inlines = [FilialInline]


@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    list_display = ["nome", "empresa", "cidade", "ativa"]
    list_filter = ["empresa", "ativa"]
    search_fields = ["nome", "cidade"]


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ["username", "first_name", "email", "papel", "empresa", "filial", "is_active"]
    list_filter = ["papel", "empresa", "filial", "is_active"]
    fieldsets = UserAdmin.fieldsets + (
        ("Acesso no grupo", {"fields": ("papel", "empresa", "filial")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Acesso no grupo", {"fields": ("first_name", "email", "papel", "empresa", "filial")}),
    )
