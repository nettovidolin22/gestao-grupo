from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import render

from quadros.models import Quadro


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
