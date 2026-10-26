from django import forms
from django.core.exceptions import ValidationError

from .models import CORES, Automacao, Coluna, Grupo, Quadro


class QuadroForm(forms.ModelForm):
    class Meta:
        model = Quadro
        fields = ["nome", "filial", "descricao"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["filial"].queryset = usuario.filiais_visiveis().select_related("empresa")


class DuplicarForm(forms.Form):
    nome = forms.CharField(max_length=120)
    com_itens = forms.BooleanField(label="Copiar também os itens", required=False)


class GrupoForm(forms.ModelForm):
    cor = forms.ChoiceField(choices=[(c, c.capitalize()) for c in CORES])

    class Meta:
        model = Grupo
        fields = ["nome", "cor", "ordem"]


def opcoes_para_texto(opcoes):
    return "\n".join(f"{o['nome']} = {o['cor']}" for o in opcoes)


class ColunaForm(forms.ModelForm):
    opcoes_texto = forms.CharField(
        label="Etiquetas (só para Status)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "A fazer = cinza\nFeito = verde"}),
        help_text="Uma por linha, no formato Nome = cor. Cores: " + ", ".join(CORES) + ".",
    )

    class Meta:
        model = Coluna
        fields = ["nome", "tipo", "ordem"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["opcoes_texto"].initial = opcoes_para_texto(self.instance.opcoes)
            # Trocar o tipo de uma coluna com dados bagunçaria os valores já salvos.
            self.fields["tipo"].disabled = True

    def clean(self):
        dados = super().clean()
        opcoes = []
        for linha in (dados.get("opcoes_texto") or "").splitlines():
            if not linha.strip():
                continue
            nome, _, cor = linha.partition("=")
            nome, cor = nome.strip(), (cor.strip().lower() or "cinza")
            if not nome:
                raise ValidationError("Cada etiqueta precisa de um nome.")
            if cor not in CORES:
                raise ValidationError(f"Cor desconhecida: {cor}. Use: {', '.join(CORES)}.")
            opcoes.append({"nome": nome[:40], "cor": cor})
        if dados.get("tipo") == Coluna.Tipo.STATUS and not opcoes:
            raise ValidationError("Uma coluna de Status precisa de pelo menos uma etiqueta.")
        self.instance.opcoes = opcoes if dados.get("tipo") == Coluna.Tipo.STATUS else []
        return dados


class AutomacaoForm(forms.ModelForm):
    class Meta:
        model = Automacao
        fields = ["coluna", "valor", "acao", "pessoa", "grupo", "ativa"]
        labels = {"coluna": "Quando a coluna", "acao": "Ação", "pessoa": "Pessoa a avisar", "grupo": "Grupo de destino"}
        help_texts = {
            "valor": "Escreva a etiqueta exatamente como aparece na coluna (ex.: Feito).",
            "pessoa": "Só para a ação “Avisar uma pessoa”.",
            "grupo": "Só para a ação “Mover o item para um grupo”.",
        }

    def __init__(self, *args, quadro, **kwargs):
        super().__init__(*args, **kwargs)
        self.quadro = quadro
        self.fields["coluna"].queryset = quadro.colunas.filter(tipo=Coluna.Tipo.STATUS)
        self.fields["pessoa"].queryset = quadro.pessoas()
        self.fields["grupo"].queryset = quadro.grupos.all()

    def clean(self):
        dados = super().clean()
        coluna, valor, acao = dados.get("coluna"), dados.get("valor"), dados.get("acao")
        if coluna and valor and valor not in [o["nome"] for o in coluna.opcoes]:
            opcoes = ", ".join(o["nome"] for o in coluna.opcoes)
            self.add_error("valor", f"Etiqueta inexistente em {coluna.nome}. Use uma destas: {opcoes}.")
        if acao == Automacao.Acao.AVISAR_PESSOA and not dados.get("pessoa"):
            self.add_error("pessoa", "Escolha quem avisar.")
        if acao == Automacao.Acao.MOVER_GRUPO and not dados.get("grupo"):
            self.add_error("grupo", "Escolha o grupo de destino.")
        self.instance.quadro = self.quadro
        return dados


class ImportarForm(forms.Form):
    arquivo = forms.FileField(help_text="Arquivo .xlsx exportado do Monday, ou .csv.")
    nome = forms.CharField(label="Nome do novo quadro", max_length=120, required=False,
                           help_text="Deixe vazio para usar o nome que vem no arquivo.")
    filial = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["filial"].queryset = usuario.filiais_visiveis().select_related("empresa")
