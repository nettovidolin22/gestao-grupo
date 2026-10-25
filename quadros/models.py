from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

from organizacao.models import Filial

CORES = ["cinza", "azul", "verde", "amarelo", "laranja", "vermelho", "roxo"]

STATUS_PADRAO = [
    {"nome": "A fazer", "cor": "cinza"},
    {"nome": "Fazendo", "cor": "laranja"},
    {"nome": "Parado", "cor": "vermelho"},
    {"nome": "Feito", "cor": "verde"},
]
PRIORIDADE_PADRAO = [
    {"nome": "Alta", "cor": "vermelho"},
    {"nome": "Média", "cor": "amarelo"},
    {"nome": "Baixa", "cor": "azul"},
]


class QuadroQuerySet(models.QuerySet):
    def visiveis_para(self, usuario):
        return self.filter(filial__in=usuario.filiais_visiveis(), arquivado=False)


class Quadro(models.Model):
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="quadros")
    nome = models.CharField(max_length=120)
    descricao = models.TextField("descrição", blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    arquivado = models.BooleanField(default=False)

    objects = QuadroQuerySet.as_manager()

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def pessoas(self):
        """Quem pode ser responsável por itens deste quadro."""
        from organizacao.models import Usuario

        P = Usuario.Papel
        return Usuario.objects.filter(is_active=True).filter(
            models.Q(papel=P.ADMIN_GRUPO)
            | models.Q(papel=P.GESTOR_EMPRESA, empresa_id=self.filial.empresa_id)
            | models.Q(filial=self.filial)
        ).order_by("first_name", "username")

    @classmethod
    def criar_padrao(cls, **campos):
        """Cria o quadro já com um grupo e as colunas mais usadas."""
        with transaction.atomic():
            quadro = cls.objects.create(**campos)
            quadro.grupos.create(nome="Tarefas", cor="azul", ordem=0)
            quadro.colunas.create(nome="Status", tipo=Coluna.Tipo.STATUS, opcoes=STATUS_PADRAO, ordem=0)
            quadro.colunas.create(nome="Responsável", tipo=Coluna.Tipo.PESSOA, ordem=1)
            quadro.colunas.create(nome="Prazo", tipo=Coluna.Tipo.DATA, ordem=2)
            quadro.colunas.create(
                nome="Prioridade", tipo=Coluna.Tipo.STATUS, opcoes=PRIORIDADE_PADRAO, ordem=3
            )
        return quadro

    def duplicar(self, nome, criado_por, com_itens=False):
        """Copia colunas e grupos (e opcionalmente os itens) para um novo quadro."""
        with transaction.atomic():
            novo = Quadro.objects.create(
                filial=self.filial, nome=nome, descricao=self.descricao, criado_por=criado_por
            )
            mapa_colunas = {}
            for coluna in self.colunas.all():
                nova = novo.colunas.create(
                    nome=coluna.nome, tipo=coluna.tipo, opcoes=coluna.opcoes, ordem=coluna.ordem
                )
                mapa_colunas[str(coluna.pk)] = str(nova.pk)
            for grupo in self.grupos.all():
                novo_grupo = novo.grupos.create(nome=grupo.nome, cor=grupo.cor, ordem=grupo.ordem)
                if com_itens:
                    for item in grupo.itens.all():
                        valores = {
                            mapa_colunas[k]: v for k, v in item.valores.items() if k in mapa_colunas
                        }
                        novo_grupo.itens.create(
                            nome=item.nome, ordem=item.ordem, valores=valores, criado_por=criado_por
                        )
        return novo


class Grupo(models.Model):
    quadro = models.ForeignKey(Quadro, on_delete=models.CASCADE, related_name="grupos")
    nome = models.CharField(max_length=120)
    cor = models.CharField(max_length=20, default="azul")
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "pk"]

    def __str__(self):
        return self.nome


class Coluna(models.Model):
    class Tipo(models.TextChoices):
        TEXTO = "texto", "Texto"
        NUMERO = "numero", "Número"
        STATUS = "status", "Status (etiquetas coloridas)"
        PESSOA = "pessoa", "Pessoa"
        DATA = "data", "Data"

    quadro = models.ForeignKey(Quadro, on_delete=models.CASCADE, related_name="colunas")
    nome = models.CharField(max_length=60)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    # Para colunas de status: [{"nome": "Feito", "cor": "verde"}, ...]
    opcoes = models.JSONField(default=list, blank=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "pk"]

    def __str__(self):
        return self.nome

    def cor_da_opcao(self, nome):
        for opcao in self.opcoes:
            if opcao["nome"] == nome:
                return opcao["cor"]
        return ""

    def limpar_valor(self, bruto):
        """Converte o texto vindo do formulário no valor guardado. Vazio vira None."""
        bruto = (bruto or "").strip()
        if not bruto:
            return None
        if self.tipo == self.Tipo.TEXTO:
            return bruto[:500]
        if self.tipo == self.Tipo.NUMERO:
            try:
                return str(Decimal(bruto.replace(",", ".")))
            except InvalidOperation:
                raise ValidationError("Informe um número.")
        if self.tipo == self.Tipo.STATUS:
            if bruto not in [o["nome"] for o in self.opcoes]:
                raise ValidationError("Opção inválida.")
            return bruto
        if self.tipo == self.Tipo.PESSOA:
            if not self.quadro.pessoas().filter(pk=bruto).exists():
                raise ValidationError("Pessoa inválida.")
            return int(bruto)
        if self.tipo == self.Tipo.DATA:
            try:
                return date.fromisoformat(bruto).isoformat()
            except ValueError:
                raise ValidationError("Data inválida.")
        raise ValidationError("Tipo de coluna desconhecido.")


class Item(models.Model):
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name="itens")
    nome = models.CharField(max_length=255)
    # Valores das colunas, chaveados pelo id da coluna: {"12": "Feito", "13": 4}
    valores = models.JSONField(default=dict, blank=True)
    ordem = models.PositiveIntegerField(default=0)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ordem", "pk"]

    def __str__(self):
        return self.nome

    def valor(self, coluna):
        return self.valores.get(str(coluna.pk))

    def definir_valor(self, coluna, bruto):
        valor = coluna.limpar_valor(bruto)
        if valor is None:
            self.valores.pop(str(coluna.pk), None)
        else:
            self.valores[str(coluna.pk)] = valor
        self.save(update_fields=["valores"])


def caminho_anexo(anexo, nome_arquivo):
    return f"anexos/quadro_{anexo.item.grupo.quadro_id}/item_{anexo.item_id}/{nome_arquivo}"


class Comentario(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="comentarios")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    texto = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "comentário"
        ordering = ["criado_em"]


class Anexo(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to=caminho_anexo)
    nome = models.CharField(max_length=255)
    tamanho = models.PositiveIntegerField(default=0)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enviado_em"]


class Subtarefa(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="subtarefas")
    nome = models.CharField(max_length=255)
    feita = models.BooleanField(default=False)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "pk"]


class Atividade(models.Model):
    """Histórico do item: quem fez o quê e quando."""

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="atividades")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    descricao = models.CharField(max_length=300)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em", "-pk"]
