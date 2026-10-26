from datetime import date, timedelta

from django.core.management.base import BaseCommand

from notificacoes.servicos import notificar
from quadros.colaboracao import STATUS_CONCLUIDO, link_item, responsaveis
from quadros.models import Coluna, Item


class Command(BaseCommand):
    help = "Avisa os responsáveis dos itens que vencem amanhã ou já venceram. Rode uma vez por dia."

    def handle(self, *args, **options):
        hoje = date.today()
        amanha = hoje + timedelta(days=1)
        enviados = 0
        itens = Item.objects.filter(grupo__quadro__arquivado=False).select_related("grupo__quadro")
        for item in itens:
            quadro = item.grupo.quadro
            colunas = list(quadro.colunas.all())
            if any(
                str(item.valor(c) or "").lower() in STATUS_CONCLUIDO
                for c in colunas
                if c.tipo == Coluna.Tipo.STATUS
            ):
                continue
            for coluna in (c for c in colunas if c.tipo == Coluna.Tipo.DATA):
                valor = item.valor(coluna)
                if not valor:
                    continue
                prazo = date.fromisoformat(valor)
                if prazo == amanha:
                    texto = f"“{item.nome}” ({quadro.nome}) vence amanhã: {coluna.nome} {prazo:%d/%m}"
                elif prazo == hoje - timedelta(days=1):
                    texto = f"“{item.nome}” ({quadro.nome}) venceu ontem: {coluna.nome} {prazo:%d/%m}"
                else:
                    continue
                for pessoa in responsaveis(item):
                    notificar(pessoa, texto, link_item(item))
                    enviados += 1
        self.stdout.write(self.style.SUCCESS(f"{enviados} aviso(s) de prazo enviado(s)."))
