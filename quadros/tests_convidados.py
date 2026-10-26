"""Pessoas de outra filial ou empresa convidadas para um quadro."""

from django.test import TestCase
from django.urls import reverse

from notificacoes.models import Notificacao
from organizacao.models import Empresa, Filial, Usuario

from .models import Coluna, Quadro

P = Usuario.Papel


class ConvidadosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        gencau = Empresa.objects.create(nome="Gencau")
        titan = Empresa.objects.create(nome="Titan")
        cls.matriz = Filial.objects.create(empresa=gencau, nome="Matriz")
        cls.fabrica = Filial.objects.create(empresa=titan, nome="Fábrica")
        cls.gestor = Usuario.objects.create_user(
            "gestor", password="x", papel=P.GESTOR_FILIAL, empresa=gencau, filial=cls.matriz
        )
        cls.colab = Usuario.objects.create_user(
            "colab", password="x", papel=P.COLABORADOR, empresa=gencau, filial=cls.matriz
        )
        cls.externo = Usuario.objects.create_user(
            "externo", password="x", papel=P.GESTOR_FILIAL, empresa=titan, filial=cls.fabrica
        )
        cls.quadro = Quadro.criar_padrao(nome="Compras", filial=cls.matriz)
        cls.pessoa = cls.quadro.colunas.get(tipo=Coluna.Tipo.PESSOA)
        cls.item = cls.quadro.grupos.first().itens.create(nome="Cotar peças", ordem=1)

    def convidar(self):
        self.client.force_login(self.gestor)
        return self.client.post(
            reverse("quadros:convidados", args=[self.quadro.pk]), {"usuario": self.externo.pk}
        )

    def test_quem_e_de_fora_nao_ve_o_quadro_antes_do_convite(self):
        self.client.force_login(self.externo)
        self.assertEqual(self.client.get(reverse("quadros:detalhe", args=[self.quadro.pk])).status_code, 404)

    def test_convidado_ve_o_quadro_e_recebe_aviso(self):
        self.convidar()
        pagina = self.client.get(reverse("quadros:convidados", args=[self.quadro.pk]))
        self.assertContains(pagina, "externo · Fábrica")
        self.assertTrue(Notificacao.objects.filter(usuario=self.externo).exists())
        self.client.force_login(self.externo)
        self.assertContains(self.client.get(reverse("quadros:lista")), "convidado")
        self.assertEqual(self.client.get(reverse("quadros:detalhe", args=[self.quadro.pk])).status_code, 200)

    def test_tarefa_pode_ser_atribuida_ao_convidado(self):
        self.convidar()
        self.client.post(
            reverse("quadros:item_valor", args=[self.item.pk, self.pessoa.pk]),
            {"valor": self.externo.pk},
        )
        self.item.refresh_from_db()
        self.assertEqual(str(self.item.valor(self.pessoa)), str(self.externo.pk))

    def test_convidado_trabalha_nos_itens_mas_nao_mexe_na_estrutura(self):
        self.convidar()
        self.client.force_login(self.externo)
        resposta = self.client.post(
            reverse("quadros:item_nome", args=[self.item.pk]), {"nome": "Cotar peças urgentes"}
        )
        self.assertLess(resposta.status_code, 400)
        for nome in ("colunas", "automacoes", "convidados", "grupo_novo"):
            self.assertEqual(self.client.get(reverse(f"quadros:{nome}", args=[self.quadro.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("quadros:editar", args=[self.quadro.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("quadros:detalhe", args=[self.quadro.pk])), "Automações")
        self.assertEqual(
            self.client.post(reverse("quadros:item_excluir", args=[self.item.pk])).status_code, 403
        )

    def test_colaborador_nao_convida(self):
        self.client.force_login(self.colab)
        self.assertEqual(self.client.get(reverse("quadros:convidados", args=[self.quadro.pk])).status_code, 403)

    def test_remover_convidado_tira_o_acesso(self):
        self.convidar()
        self.client.post(reverse("quadros:convidado_remover", args=[self.quadro.pk, self.externo.pk]))
        self.client.force_login(self.externo)
        self.assertEqual(self.client.get(reverse("quadros:detalhe", args=[self.quadro.pk])).status_code, 404)

    def test_painel_do_convidado_nao_mostra_quadro_de_fora(self):
        self.convidar()
        self.client.force_login(self.externo)
        self.assertNotContains(self.client.get(reverse("quadros:painel_gerencial")), "Compras")
