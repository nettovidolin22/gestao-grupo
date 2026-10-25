from itertools import groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Max, Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ColunaForm, DuplicarForm, GrupoForm, QuadroForm
from .models import Coluna, Grupo, Item, Quadro


def pode_gerenciar(usuario):
    """Gestores e administradores mexem na estrutura (quadros, grupos, colunas)."""
    return usuario.ve_grupo_todo or usuario.papel != usuario.Papel.COLABORADOR


def exigir_gestor(usuario):
    if not pode_gerenciar(usuario):
        raise PermissionDenied("Só gestores podem alterar a estrutura do quadro.")


def quadro_do_usuario(usuario, pk):
    return get_object_or_404(Quadro.objects.visiveis_para(usuario).select_related("filial"), pk=pk)


def item_do_usuario(usuario, pk):
    return get_object_or_404(
        Item.objects.select_related("grupo__quadro__filial"),
        pk=pk,
        grupo__quadro__in=Quadro.objects.visiveis_para(usuario),
    )


def htmx(request):
    return request.headers.get("HX-Request") == "true"


def proxima_ordem(queryset):
    return (queryset.aggregate(m=Max("ordem"))["m"] or 0) + 1


@login_required
def lista(request):
    quadros = Quadro.objects.visiveis_para(request.user).select_related("filial__empresa")
    quadros = sorted(quadros, key=lambda q: (str(q.filial), q.nome))
    por_filial = [(filial, list(qs)) for filial, qs in groupby(quadros, key=lambda q: q.filial)]
    return render(
        request,
        "quadros/lista.html",
        {"por_filial": por_filial, "pode_gerenciar": pode_gerenciar(request.user)},
    )


@login_required
def novo(request):
    exigir_gestor(request.user)
    form = QuadroForm(request.POST or None, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        quadro = Quadro.criar_padrao(criado_por=request.user, **form.cleaned_data)
        return redirect("quadros:detalhe", pk=quadro.pk)
    return render(request, "quadros/form.html", {"form": form, "titulo": "Novo quadro"})


@login_required
def editar(request, pk):
    exigir_gestor(request.user)
    quadro = quadro_do_usuario(request.user, pk)
    form = QuadroForm(request.POST or None, instance=quadro, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("quadros:detalhe", pk=quadro.pk)
    return render(
        request, "quadros/form.html", {"form": form, "titulo": "Editar quadro", "quadro": quadro}
    )


@login_required
@require_POST
def arquivar(request, pk):
    exigir_gestor(request.user)
    quadro = quadro_do_usuario(request.user, pk)
    quadro.arquivado = True
    quadro.save(update_fields=["arquivado"])
    messages.success(request, f"Quadro “{quadro.nome}” arquivado.")
    return redirect("quadros:lista")


@login_required
def duplicar(request, pk):
    exigir_gestor(request.user)
    quadro = quadro_do_usuario(request.user, pk)
    form = DuplicarForm(request.POST or None, initial={"nome": f"{quadro.nome} (cópia)"})
    if request.method == "POST" and form.is_valid():
        novo_quadro = quadro.duplicar(criado_por=request.user, **form.cleaned_data)
        return redirect("quadros:detalhe", pk=novo_quadro.pk)
    return render(
        request, "quadros/form.html", {"form": form, "titulo": "Duplicar quadro", "quadro": quadro}
    )


@login_required
def detalhe(request, pk):
    quadro = quadro_do_usuario(request.user, pk)
    grupos = quadro.grupos.prefetch_related(Prefetch("itens", queryset=Item.objects.all()))
    return render(
        request,
        "quadros/detalhe.html",
        {
            "quadro": quadro,
            "grupos": grupos,
            "colunas": list(quadro.colunas.all()),
            "pessoas": list(quadro.pessoas()),
            "pode_gerenciar": pode_gerenciar(request.user),
        },
    )


def render_linha(request, item, colunas=None, pessoas=None):
    quadro = item.grupo.quadro
    return render(
        request,
        "quadros/_linha.html",
        {
            "item": item,
            "colunas": colunas if colunas is not None else list(quadro.colunas.all()),
            "pessoas": pessoas if pessoas is not None else list(quadro.pessoas()),
        },
    )


@login_required
@require_POST
def item_criar(request, grupo_pk):
    grupo = get_object_or_404(
        Grupo, pk=grupo_pk, quadro__in=Quadro.objects.visiveis_para(request.user)
    )
    nome = request.POST.get("nome", "").strip()[:255]
    if not nome:
        return HttpResponse(status=204)
    item = grupo.itens.create(nome=nome, ordem=proxima_ordem(grupo.itens), criado_por=request.user)
    if htmx(request):
        return render_linha(request, item)
    return redirect("quadros:detalhe", pk=grupo.quadro_id)


@login_required
@require_POST
def item_nome(request, pk):
    item = item_do_usuario(request.user, pk)
    nome = request.POST.get("nome", "").strip()[:255]
    if nome:
        item.nome = nome
        item.save(update_fields=["nome"])
    if htmx(request):
        return HttpResponse(status=204)
    return redirect("quadros:detalhe", pk=item.grupo.quadro_id)


@login_required
@require_POST
def item_valor(request, pk, coluna_pk):
    item = item_do_usuario(request.user, pk)
    coluna = get_object_or_404(Coluna, pk=coluna_pk, quadro_id=item.grupo.quadro_id)
    erro = None
    try:
        item.definir_valor(coluna, request.POST.get("valor"))
    except ValidationError as e:
        erro = e.messages[0]
    if htmx(request):
        return render(
            request,
            "quadros/_celula.html",
            {"item": item, "coluna": coluna, "pessoas": item.grupo.quadro.pessoas(), "erro": erro},
        )
    if erro:
        messages.error(request, erro)
    return redirect("quadros:detalhe", pk=item.grupo.quadro_id)


@login_required
@require_POST
def item_excluir(request, pk):
    item = item_do_usuario(request.user, pk)
    quadro_pk = item.grupo.quadro_id
    item.delete()
    if htmx(request):
        return HttpResponse("")
    return redirect("quadros:detalhe", pk=quadro_pk)


@login_required
def grupo_form(request, quadro_pk, pk=None):
    exigir_gestor(request.user)
    quadro = quadro_do_usuario(request.user, quadro_pk)
    grupo = get_object_or_404(Grupo, pk=pk, quadro=quadro) if pk else None
    inicial = {} if grupo else {"ordem": proxima_ordem(quadro.grupos)}
    form = GrupoForm(request.POST or None, instance=grupo, initial=inicial)
    if request.method == "POST" and form.is_valid():
        form.instance.quadro = quadro
        form.save()
        return redirect("quadros:detalhe", pk=quadro.pk)
    titulo = "Editar grupo" if grupo else "Novo grupo"
    return render(
        request,
        "quadros/form.html",
        {"form": form, "titulo": titulo, "quadro": quadro, "grupo": grupo},
    )


@login_required
@require_POST
def grupo_excluir(request, quadro_pk, pk):
    exigir_gestor(request.user)
    quadro = quadro_do_usuario(request.user, quadro_pk)
    grupo = get_object_or_404(Grupo, pk=pk, quadro=quadro)
    if quadro.grupos.count() == 1:
        messages.error(request, "O quadro precisa ter pelo menos um grupo.")
    else:
        grupo.delete()
        messages.success(request, f"Grupo “{grupo.nome}” excluído com seus itens.")
    return redirect("quadros:detalhe", pk=quadro.pk)


@login_required
def colunas(request, quadro_pk):
    exigir_gestor(request.user)
    quadro = quadro_do_usuario(request.user, quadro_pk)
    return render(
        request,
        "quadros/colunas.html",
        {"quadro": quadro, "colunas": quadro.colunas.all()},
    )


@login_required
def coluna_form(request, quadro_pk, pk=None):
    exigir_gestor(request.user)
    quadro = quadro_do_usuario(request.user, quadro_pk)
    coluna = get_object_or_404(Coluna, pk=pk, quadro=quadro) if pk else None
    inicial = {} if coluna else {"ordem": proxima_ordem(quadro.colunas)}
    form = ColunaForm(request.POST or None, instance=coluna, initial=inicial)
    if request.method == "POST" and form.is_valid():
        form.instance.quadro = quadro
        form.save()
        return redirect("quadros:colunas", quadro_pk=quadro.pk)
    titulo = "Editar coluna" if coluna else "Nova coluna"
    return render(
        request,
        "quadros/form.html",
        {"form": form, "titulo": titulo, "quadro": quadro, "coluna": coluna},
    )


@login_required
@require_POST
def coluna_excluir(request, quadro_pk, pk):
    exigir_gestor(request.user)
    quadro = quadro_do_usuario(request.user, quadro_pk)
    coluna = get_object_or_404(Coluna, pk=pk, quadro=quadro)
    chave = str(coluna.pk)
    for grupo in quadro.grupos.all():
        for item in grupo.itens.all():
            if chave in item.valores:
                del item.valores[chave]
                item.save(update_fields=["valores"])
    coluna.delete()
    messages.success(request, f"Coluna “{coluna.nome}” excluída.")
    return redirect("quadros:colunas", quadro_pk=quadro.pk)
