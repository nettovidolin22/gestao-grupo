from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from organizacao.models import Empresa, Filial, Usuario

from .models import Coluna, Quadro

P = Usuario.Papel


class QuadrosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        alfa = Empresa.objects.create(nome="Alfa")
        cls.matriz = Filial.objects.create(empresa=alfa, nome="Matriz")
        cls.filial2 = Filial.objects.create(empresa=alfa, nome="Filial 2")
        cls.gestor = Usuario.objects.create_user(
            "gestor", password="x", papel=P.GESTOR_EMPRESA, empresa=alfa
        )
        cls.colab = Usuario.objects.create_user(
            "colab", password="x", papel=P.COLABORADOR, empresa=alfa, filial=cls.matriz
        )
        cls.outro = Usuario.objects.create_user(
            "outro", password="x", papel=P.COLABORADOR, empresa=alfa, filial=cls.filial2
        )
        cls.quadro = Quadro.criar_padrao(nome="Manutenção", filial=cls.matriz)
        cls.status = cls.quadro.colunas.get(nome="Status")
        cls.item = cls.quadro.grupos.first().itens.create(nome="Trocar lâmpada")

    def test_quadro_padrao_tem_grupo_e_colunas(self):
        self.assertEqual(self.quadro.grupos.count(), 1)
        self.assertEqual(
            list(self.quadro.colunas.values_list("nome", flat=True)),
            ["Status", "Responsável", "Prazo", "Prioridade"],
        )

    def test_colaborador_ve_so_quadros_da_propria_filial(self):
        self.assertIn(self.quadro, Quadro.objects.visiveis_para(self.colab))
        self.assertNotIn(self.quadro, Quadro.objects.visiveis_para(self.outro))

    def test_quadro_de_outra_filial_da_404(self):
        self.client.login(username="outro", password="x")
        resposta = self.client.get(reverse("quadros:detalhe", args=[self.quadro.pk]))
        self.assertEqual(resposta.status_code, 404)
        resposta = self.client.post(
            reverse("quadros:item_valor", args=[self.item.pk, self.status.pk]), {"valor": "Feito"}
        )
        self.assertEqual(resposta.status_code, 404)

    def test_colaborador_nao_cria_quadro(self):
        self.client.login(username="colab", password="x")
        self.assertEqual(self.client.get(reverse("quadros:novo")).status_code, 403)

    def test_gestor_cria_quadro(self):
        self.client.login(username="gestor", password="x")
        resposta = self.client.post(
            reverse("quadros:novo"), {"nome": "Compras", "filial": self.filial2.pk}
        )
        quadro = Quadro.objects.get(nome="Compras")
        self.assertRedirects(resposta, reverse("quadros:detalhe", args=[quadro.pk]))

    def test_colaborador_edita_valor_pela_tela(self):
        self.client.login(username="colab", password="x")
        resposta = self.client.post(
            reverse("quadros:item_valor", args=[self.item.pk, self.status.pk]),
            {"valor": "Feito"},
            HTTP_HX_REQUEST="true",
        )
        self.assertContains(resposta, "cor-verde")
        self.item.refresh_from_db()
        self.assertEqual(self.item.valor(self.status), "Feito")

    def test_colaborador_cria_item(self):
        self.client.login(username="colab", password="x")
        grupo = self.quadro.grupos.first()
        resposta = self.client.post(
            reverse("quadros:item_criar", args=[grupo.pk]), {"nome": "Pintar parede"},
            HTTP_HX_REQUEST="true",
        )
        self.assertContains(resposta, "Pintar parede")

    def test_validacao_dos_valores(self):
        numero = self.quadro.colunas.create(nome="Custo", tipo=Coluna.Tipo.NUMERO)
        self.assertEqual(numero.limpar_valor("12,50"), "12.50")
        with self.assertRaises(ValidationError):
            numero.limpar_valor("abc")
        with self.assertRaises(ValidationError):
            self.status.limpar_valor("Inexistente")
        pessoa = self.quadro.colunas.get(nome="Responsável")
        self.assertEqual(pessoa.limpar_valor(str(self.colab.pk)), self.colab.pk)
        with self.assertRaises(ValidationError):
            pessoa.limpar_valor(str(self.outro.pk))  # de outra filial
        self.assertIsNone(self.status.limpar_valor(""))

    def test_duplicar_copia_estrutura_e_itens(self):
        self.item.definir_valor(self.status, "Feito")
        copia = self.quadro.duplicar(nome="Cópia", criado_por=self.gestor, com_itens=True)
        self.assertEqual(copia.colunas.count(), 4)
        item = copia.grupos.first().itens.get()
        self.assertEqual(item.valor(copia.colunas.get(nome="Status")), "Feito")

    def test_excluir_coluna_limpa_valores(self):
        self.item.definir_valor(self.status, "Feito")
        self.client.login(username="gestor", password="x")
        self.client.post(reverse("quadros:coluna_excluir", args=[self.quadro.pk, self.status.pk]))
        self.item.refresh_from_db()
        self.assertEqual(self.item.valores, {})

    def test_coluna_status_exige_etiquetas(self):
        self.client.login(username="gestor", password="x")
        url = reverse("quadros:coluna_nova", args=[self.quadro.pk])
        resposta = self.client.post(url, {"nome": "Fase", "tipo": "status", "ordem": 5})
        self.assertContains(resposta, "pelo menos uma etiqueta")
        self.client.post(
            url, {"nome": "Fase", "tipo": "status", "ordem": 5, "opcoes_texto": "Início = azul\nFim = verde"}
        )
        fase = self.quadro.colunas.get(nome="Fase")
        self.assertEqual(fase.opcoes[1], {"nome": "Fim", "cor": "verde"})
