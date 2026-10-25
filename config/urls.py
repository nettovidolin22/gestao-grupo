from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from organizacao import views

admin.site.site_header = "Gestão do Grupo"
admin.site.site_title = "Gestão do Grupo"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("entrar/", auth_views.LoginView.as_view(), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "senha/alterar/",
        auth_views.PasswordChangeView.as_view(success_url="/"),
        name="password_change",
    ),
    path("admin/", admin.site.urls),
]
