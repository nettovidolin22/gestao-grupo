"""Números do painel gerencial, calculados a partir dos quadros visíveis."""

from collections import defaultdict
from datetime import date, timedelta

from .colaboracao import STATUS_CONCLUIDO
from .models import Coluna, Item, Quadro


def resumo(usuario, empresa_id=None, filial_id=None):
    hoje = date.today()
    em_7_dias = hoje + timedelta(days=7)
    quadros = Quadro.objects.da_area_de(usuario).select_related("filial__empresa")
    if empresa_id:
        quadros = quadros.filter(filial__empresa_id=empresa_id)
    if filial_id:
        quadros = quadros.filter(filial_id=filial_id)
    quadros = list(quadros.prefetch_related("colunas"))
    colunas = {q.pk: list(q.colunas.all()) for q in quadros}
    por_quadro = {q.pk: q for q in quadros}

    totais = {"itens": 0, "abertos": 0, "concluidos": 0, "atrasados": 0, "semana": 0}
    filiais = defaultdict(lambda: {"quadros": set(), "abertos": 0, "concluidos": 0, "atrasados": 0})
    pessoas = defaultdict(lambda: {"abertos": 0, "atrasados": 0})
    atrasados = []

    itens = Item.objects.filter(grupo__quadro__in=quadros).select_related("grupo")
    for item in itens:
        quadro = por_quadro[item.grupo.quadro_id]
        cols = colunas[quadro.pk]
        status = [c for c in cols if c.tipo == Coluna.Tipo.STATUS]
        concluido = bool(status) and str(item.valor(status[0]) or "").lower() in STATUS_CONCLUIDO
        prazos = [
            date.fromisoformat(item.valor(c)) for c in cols if c.tipo == Coluna.Tipo.DATA and item.valor(c)
        ]
        responsaveis = [item.valor(c) for c in cols if c.tipo == Coluna.Tipo.PESSOA and item.valor(c)]
        atrasado = not concluido and any(p < hoje for p in prazos)
        filial = filiais[quadro.filial]
        filial["quadros"].add(quadro.pk)
        totais["itens"] += 1
        if concluido:
            totais["concluidos"] += 1
            filial["concluidos"] += 1
            continue
        totais["abertos"] += 1
        filial["abertos"] += 1
        if atrasado:
            totais["atrasados"] += 1
            filial["atrasados"] += 1
            atrasados.append({"item": item, "quadro": quadro, "prazo": min(prazos), "responsaveis": responsaveis})
        elif any(hoje <= p <= em_7_dias for p in prazos):
            totais["semana"] += 1
        for pessoa_id in responsaveis:
            pessoas[pessoa_id]["abertos"] += 1
            if atrasado:
                pessoas[pessoa_id]["atrasados"] += 1

    for q in quadros:  # filiais com quadros vazios também aparecem
        filiais[q.filial]["quadros"].add(q.pk)
    linhas_filiais = []
    for filial, dados in sorted(filiais.items(), key=lambda par: str(par[0])):
        total = dados["abertos"] + dados["concluidos"]
        linhas_filiais.append({
            "filial": filial,
            "quadros": len(dados["quadros"]),
            "abertos": dados["abertos"],
            "concluidos": dados["concluidos"],
            "atrasados": dados["atrasados"],
            "percentual": round(100 * dados["concluidos"] / total) if total else 0,
        })

    from organizacao.models import Usuario

    nomes = {u.pk: u.get_full_name() or u.username for u in Usuario.objects.filter(pk__in=pessoas)}
    linhas_pessoas = sorted(
        ({"nome": nomes.get(pk, "Pessoa removida"), **dados} for pk, dados in pessoas.items()),
        key=lambda linha: (-linha["atrasados"], -linha["abertos"], linha["nome"]),
    )
    for linha in atrasados:
        linha["responsaveis"] = ", ".join(nomes.get(pk, "") for pk in linha["responsaveis"])
    atrasados.sort(key=lambda linha: linha["prazo"])
    return {
        "totais": totais,
        "por_filial": linhas_filiais,
        "pessoas": linhas_pessoas,
        "atrasados": atrasados[:30],
        "hoje": hoje,
    }
