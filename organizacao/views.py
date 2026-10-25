from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def painel(request):
    usuario = request.user
    filiais = usuario.filiais_visiveis().select_related("empresa")
    empresas = {}
    for filial in filiais:
        empresas.setdefault(filial.empresa, []).append(filial)
    return render(request, "organizacao/painel.html", {"empresas": empresas})
