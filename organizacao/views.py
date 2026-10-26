from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render

from quadros.models import Quadro

from .forms import UsuarioForm
from .models import TentativaLogin


@login_required
def painel(request):
    usuario = request.user
    filiais = usuario.filiais_visiveis().select_related("empresa").prefetch_related(
        Prefetch("quadros", queryset=Quadro.objects.filter(arquivado=False), to_attr="quadros_ativos")
    )
    empresas = {}
    for filial in filiais:
        empresas.setdefault(filial.empresa, []).append(filial)
    return render(request, "organizacao/painel.html", {"empresas": empresas})


def exigir_gestor_de_usuarios(usuario):
    if not usuario.gerencia_usuarios:
        raise PermissionDenied("Só gestores cadastram usuários.")


@login_required
def usuarios(request):
    exigir_gestor_de_usuarios(request.user)
    lista = request.user.usuarios_gerenciaveis().select_related("empresa", "filial")
    busca = request.GET.get("q", "").strip()
    if busca:
        lista = lista.filter(
            Q(username__icontains=busca) | Q(first_name__icontains=busca)
            | Q(last_name__icontains=busca) | Q(email__icontains=busca)
        )
    lista = lista.order_by("-is_active", "first_name", "username")
    return render(request, "organizacao/usuarios.html", {"usuarios": lista, "busca": busca})


@login_required
def usuario_form(request, pk=None):
    exigir_gestor_de_usuarios(request.user)
    usuario = get_object_or_404(request.user.usuarios_gerenciaveis(), pk=pk) if pk else None
    form = UsuarioForm(request.POST or None, instance=usuario, gestor=request.user)
    if request.method == "POST" and form.is_valid():
        salvo = form.save()
        messages.success(request, f"Usuário {salvo.username} {'atualizado' if usuario else 'cadastrado'}.")
        return redirect("usuarios")
    return render(request, "organizacao/usuario_form.html", {"form": form, "usuario": usuario})


@login_required
def usuario_senha(request, pk):
    exigir_gestor_de_usuarios(request.user)
    usuario = get_object_or_404(request.user.usuarios_gerenciaveis(), pk=pk)
    form = SetPasswordForm(usuario, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        TentativaLogin.objects.filter(username=usuario.username.lower()).delete()
        messages.success(request, f"Senha de {usuario.username} redefinida. Peça para trocar no próximo acesso.")
        return redirect("usuarios")
    return render(
        request, "organizacao/usuario_form.html",
        {"form": form, "usuario": usuario, "titulo": f"Nova senha para {usuario.username}"},
    )
