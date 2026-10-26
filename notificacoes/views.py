from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Notificacao


@login_required
def lista(request):
    notificacoes = request.user.notificacoes.all()[:100]
    return render(request, "notificacoes/lista.html", {"notificacoes": notificacoes})


@login_required
def abrir(request, pk):
    notificacao = get_object_or_404(Notificacao, pk=pk, usuario=request.user)
    notificacao.lida = True
    notificacao.save(update_fields=["lida"])
    if notificacao.link and url_has_allowed_host_and_scheme(notificacao.link, allowed_hosts=None):
        return redirect(notificacao.link)
    return redirect("notificacoes:lista")


@login_required
@require_POST
def marcar_todas(request):
    request.user.notificacoes.filter(lida=False).update(lida=True)
    return redirect("notificacoes:lista")
