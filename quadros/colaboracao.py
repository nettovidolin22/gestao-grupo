"""Histórico, menções e notificações ligados aos itens dos quadros."""

import re

from django.urls import reverse

from notificacoes.servicos import notificar

from .models import Atividade, Automacao, Coluna

MENCAO = re.compile(r"@([\w.@+-]+)")

# Etiquetas de status que significam "terminado" (sem prazo a cobrar).
STATUS_CONCLUIDO = {"feito", "concluído", "concluido", "pronto", "entregue", "done"}


def link_item(item):
    return reverse("quadros:item_detalhe", args=[item.pk])


def nome_pessoa(usuario):
    return usuario.get_full_name() or usuario.username


def valor_legivel(coluna, valor, quadro):
    if valor in (None, ""):
        return "vazio"
    if coluna.tipo == Coluna.Tipo.PESSOA:
        pessoa = quadro.pessoas().filter(pk=valor).first()
        return nome_pessoa(pessoa) if pessoa else "pessoa removida"
    if coluna.tipo == Coluna.Tipo.DATA:
        ano, mes, dia = str(valor).split("-")
        return f"{dia}/{mes}/{ano}"
    return str(valor)


def registrar(item, usuario, descricao):
    return Atividade.objects.create(item=item, usuario=usuario, descricao=descricao[:300])


def responsaveis(item):
    """Pessoas atribuídas ao item em qualquer coluna do tipo Pessoa."""
    quadro = item.grupo.quadro
    ids = [
        item.valor(c) for c in quadro.colunas.filter(tipo=Coluna.Tipo.PESSOA) if item.valor(c)
    ]
    return list(quadro.pessoas().filter(pk__in=ids))


def ao_mudar_valor(item, coluna, anterior, usuario):
    novo = item.valor(coluna)
    if novo == anterior:
        return
    quadro = item.grupo.quadro
    registrar(
        item,
        usuario,
        f"mudou {coluna.nome} de {valor_legivel(coluna, anterior, quadro)} "
        f"para {valor_legivel(coluna, novo, quadro)}",
    )
    if coluna.tipo == Coluna.Tipo.STATUS and novo:
        rodar_automacoes(item, coluna, novo, usuario)
    if coluna.tipo == Coluna.Tipo.PESSOA and novo:
        pessoa = quadro.pessoas().filter(pk=novo).first()
        notificar(
            pessoa,
            f"{nome_pessoa(usuario)} atribuiu a você “{item.nome}” em {quadro.nome}",
            link_item(item),
            autor=usuario,
        )


def ao_comentar(comentario):
    item, autor = comentario.item, comentario.autor
    quadro = item.grupo.quadro
    registrar(item, autor, "comentou")
    nomes = set(MENCAO.findall(comentario.texto))
    mencionados = list(quadro.pessoas().filter(username__in=nomes)) if nomes else []
    for pessoa in mencionados:
        notificar(
            pessoa,
            f"{nome_pessoa(autor)} mencionou você em “{item.nome}”: {comentario.texto[:120]}",
            link_item(item),
            autor=autor,
        )
    for pessoa in responsaveis(item):
        if pessoa not in mencionados:
            notificar(
                pessoa,
                f"{nome_pessoa(autor)} comentou em “{item.nome}”: {comentario.texto[:120]}",
                link_item(item),
                autor=autor,
            )


def rodar_automacoes(item, coluna, valor, usuario):
    regras = Automacao.objects.filter(coluna=coluna, valor=valor, ativa=True).select_related(
        "pessoa", "grupo"
    )
    quadro = item.grupo.quadro
    texto = f"“{item.nome}” ({quadro.nome}) mudou {coluna.nome} para {valor}"
    for regra in regras:
        if regra.acao == Automacao.Acao.AVISAR_PESSOA:
            # A pessoa pode ter saído da filial depois que a regra foi criada.
            if not quadro.pessoas().filter(pk=regra.pessoa_id).exists():
                continue
            notificar(regra.pessoa, texto, link_item(item), autor=usuario)
        elif regra.acao == Automacao.Acao.AVISAR_RESPONSAVEIS:
            for pessoa in responsaveis(item):
                notificar(pessoa, texto, link_item(item), autor=usuario)
        elif regra.acao == Automacao.Acao.MOVER_GRUPO and regra.grupo_id != item.grupo_id:
            item.grupo = regra.grupo
            item.save(update_fields=["grupo"])
            registrar(item, None, f"automação moveu para o grupo {regra.grupo.nome}")
