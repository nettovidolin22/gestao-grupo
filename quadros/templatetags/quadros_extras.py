from django import template

register = template.Library()


@register.filter
def valor_de(item, coluna):
    return item.valor(coluna)


@register.filter
def cor_de(coluna, nome):
    return coluna.cor_da_opcao(nome)
