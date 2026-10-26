from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Empresa, Filial, Usuario


def so_administradores(request):
    """Cadastros (admin) só para o administrador do grupo: ali se vê e muda tudo."""
    usuario = request.user
    return usuario.is_active and usuario.is_staff and usuario.ve_grupo_todo


admin.site.has_permission = so_administradores


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
    def get_queryset(self, request):
        # O administrador do grupo não vê nem troca a senha de um superusuário.
        qs = super().get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(is_superuser=False)

    def get_readonly_fields(self, request, obj=None):
        # Só um superusuário cria outro superusuário ou dá permissões avulsas.
        if request.user.is_superuser:
            return super().get_readonly_fields(request, obj)
        return ("is_superuser", "user_permissions", "groups", "last_login", "date_joined")

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Acesso no grupo", {"fields": ("first_name", "email", "papel", "empresa", "filial")}),
    )
