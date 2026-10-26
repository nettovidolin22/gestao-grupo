from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from organizacao import views
from organizacao.forms import LoginForm

admin.site.site_header = "Gestão do Grupo"
admin.site.site_title = "Gestão do Grupo"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("entrar/", auth_views.LoginView.as_view(form_class=LoginForm), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "senha/alterar/",
        auth_views.PasswordChangeView.as_view(success_url="/"),
        name="password_change",
    ),
    path("quadros/", include("quadros.urls")),
    path("notificacoes/", include("notificacoes.urls")),
    path("admin/", admin.site.urls),
]
