from django import template

register = template.Library()


@register.filter
def valor_de(item, coluna):
    return item.valor(coluna)


@register.filter
def cor_de(coluna, nome):
    return coluna.cor_da_opcao(nome)


@register.filter
def cor_item(item, coluna):
    """Cor da etiqueta de status do item nessa coluna (vazio se não houver)."""
    if not coluna:
        return ""
    return coluna.cor_da_opcao(item.valor(coluna))


@register.filter
def chave(dicionario, chave):
    return dicionario.get(chave)


@register.filter
def data_br(valor):
    """'2026-11-30' -> '30/11/2026'."""
    if not valor:
        return ""
    ano, mes, dia = str(valor).split("-")
    return f"{dia}/{mes}/{ano}"
