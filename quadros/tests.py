import tempfile
from datetime import date, timedelta
from io import StringIO

from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
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


class VisualizacoesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        alfa = Empresa.objects.create(nome="Alfa")
        matriz = Filial.objects.create(empresa=alfa, nome="Matriz")
        Usuario.objects.create_user(
            "colab", password="x", papel=P.COLABORADOR, empresa=alfa, filial=matriz
        )
        cls.quadro = Quadro.criar_padrao(nome="Manutenção", filial=matriz)
        cls.status = cls.quadro.colunas.get(nome="Status")
        cls.prazo = cls.quadro.colunas.get(nome="Prazo")
        grupo = cls.quadro.grupos.first()
        cls.feito = grupo.itens.create(nome="Item feito")
        cls.feito.definir_valor(cls.status, "Feito")
        cls.feito.definir_valor(cls.prazo, "2026-11-30")
        cls.sem_nada = grupo.itens.create(nome="Item sem status")

    def setUp(self):
        self.client.login(username="colab", password="x")
        self.url = reverse("quadros:detalhe", args=[self.quadro.pk])

    def test_kanban_separa_por_status(self):
        resposta = self.client.get(self.url, {"visao": "kanban"})
        raias = {r["nome"]: [i.nome for i in r["itens"]] for r in resposta.context["raias"]}
        self.assertEqual(raias["Feito"], ["Item feito"])
        self.assertEqual(raias[""], ["Item sem status"])
        self.assertEqual(raias["A fazer"], [])

    def test_calendario_coloca_item_no_dia(self):
        resposta = self.client.get(self.url, {"visao": "calendario", "mes": "2026-11"})
        self.assertContains(resposta, "Novembro de 2026")
        dias = {d["dia"].isoformat(): d["itens"] for s in resposta.context["semanas"] for d in s}
        self.assertEqual([i.nome for i in dias["2026-11-30"]], ["Item feito"])
        self.assertEqual([i.nome for i in resposta.context["sem_data"]], ["Item sem status"])

    def test_mes_invalido_usa_mes_atual(self):
        resposta = self.client.get(self.url, {"visao": "calendario", "mes": "abc"})
        self.assertEqual(resposta.status_code, 200)

    def test_quadro_sem_coluna_de_status_explica_no_kanban(self):
        self.status.delete()
        self.quadro.colunas.filter(tipo=Coluna.Tipo.STATUS).delete()
        resposta = self.client.get(self.url, {"visao": "kanban"})
        self.assertContains(resposta, "ainda não tem nenhuma")

    def test_visao_desconhecida_mostra_tabela(self):
        resposta = self.client.get(self.url, {"visao": "xyz"})
        self.assertEqual(resposta.context["visao"], "tabela")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ColaboracaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        alfa = Empresa.objects.create(nome="Alfa")
        cls.matriz = Filial.objects.create(empresa=alfa, nome="Matriz")
        filial2 = Filial.objects.create(empresa=alfa, nome="Filial 2")
        cls.ana = Usuario.objects.create_user(
            "ana", password="x", email="ana@x.com", papel=P.COLABORADOR, empresa=alfa, filial=cls.matriz
        )
        cls.bia = Usuario.objects.create_user(
            "bia", password="x", email="bia@x.com", papel=P.COLABORADOR, empresa=alfa, filial=cls.matriz
        )
        cls.outro = Usuario.objects.create_user(
            "outro", password="x", papel=P.COLABORADOR, empresa=alfa, filial=filial2
        )
        cls.quadro = Quadro.criar_padrao(nome="Manutenção", filial=cls.matriz)
        cls.responsavel = cls.quadro.colunas.get(nome="Responsável")
        cls.status = cls.quadro.colunas.get(nome="Status")
        cls.prazo = cls.quadro.colunas.get(nome="Prazo")
        cls.item = cls.quadro.grupos.first().itens.create(nome="Revisar extintores")

    def setUp(self):
        self.client.login(username="ana", password="x")

    def url(self, nome, *args):
        return reverse(f"quadros:{nome}", args=args or [self.item.pk])

    def test_atribuir_responsavel_notifica_e_registra(self):
        self.client.post(
            self.url("item_valor", self.item.pk, self.responsavel.pk), {"valor": self.bia.pk}
        )
        self.assertEqual(self.bia.notificacoes.count(), 1)
        self.assertIn("atribuiu a você", self.bia.notificacoes.get().texto)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["bia@x.com"])
        self.assertIn("mudou Responsável de vazio para bia", self.item.atividades.get().descricao)

    def test_nao_notifica_a_si_mesmo(self):
        self.client.post(
            self.url("item_valor", self.item.pk, self.responsavel.pk), {"valor": self.ana.pk}
        )
        self.assertEqual(self.ana.notificacoes.count(), 0)

    def test_mencao_notifica_so_quem_ve_o_quadro(self):
        self.client.post(self.url("comentario_criar"), {"texto": "Olha isso @bia e @outro"})
        self.assertEqual(self.item.comentarios.count(), 1)
        self.assertEqual(self.bia.notificacoes.count(), 1)
        self.assertIn("mencionou você", self.bia.notificacoes.get().texto)
        self.assertEqual(self.outro.notificacoes.count(), 0)

    def test_comentario_avisa_responsavel(self):
        self.item.definir_valor(self.responsavel, str(self.bia.pk))
        self.client.post(self.url("comentario_criar"), {"texto": "Já comprei as peças"})
        self.assertIn("comentou", self.bia.notificacoes.get().texto)

    def test_so_o_autor_exclui_comentario(self):
        comentario = self.item.comentarios.create(autor=self.bia, texto="oi")
        resposta = self.client.post(self.url("comentario_excluir", comentario.pk))
        self.assertEqual(resposta.status_code, 404)
        self.assertTrue(self.item.comentarios.exists())

    def test_anexo_envia_baixa_e_bloqueia_outra_filial(self):
        arquivo = SimpleUploadedFile("nota.pdf", b"conteudo", content_type="application/pdf")
        self.client.post(self.url("anexo_enviar"), {"arquivo": arquivo})
        anexo = self.item.anexos.get()
        resposta = self.client.get(self.url("anexo_baixar", anexo.pk))
        self.assertEqual(b"".join(resposta.streaming_content), b"conteudo")
        self.client.login(username="outro", password="x")
        self.assertEqual(self.client.get(self.url("anexo_baixar", anexo.pk)).status_code, 404)

    @override_settings(TAMANHO_MAXIMO_ANEXO=5)
    def test_anexo_grande_e_recusado(self):
        arquivo = SimpleUploadedFile("grande.txt", b"123456789")
        self.client.post(self.url("anexo_enviar"), {"arquivo": arquivo})
        self.assertFalse(self.item.anexos.exists())

    def test_subtarefas(self):
        self.client.post(self.url("subtarefa_criar"), {"nome": "Comprar carga"})
        subtarefa = self.item.subtarefas.get()
        self.client.post(self.url("subtarefa_alternar", subtarefa.pk))
        subtarefa.refresh_from_db()
        self.assertTrue(subtarefa.feita)

    def test_pagina_do_item(self):
        self.item.comentarios.create(autor=self.bia, texto="Primeiro comentário")
        resposta = self.client.get(self.url("item_detalhe"))
        self.assertContains(resposta, "Primeiro comentário")
        self.client.login(username="outro", password="x")
        self.assertEqual(self.client.get(self.url("item_detalhe")).status_code, 404)

    def test_avisar_prazos(self):
        amanha = (date.today() + timedelta(days=1)).isoformat()
        self.item.definir_valor(self.responsavel, str(self.bia.pk))
        self.item.definir_valor(self.prazo, amanha)
        feito = self.quadro.grupos.first().itens.create(nome="Já feito")
        feito.definir_valor(self.responsavel, str(self.bia.pk))
        feito.definir_valor(self.prazo, amanha)
        feito.definir_valor(self.status, "Feito")
        call_command("avisar_prazos", stdout=StringIO())
        textos = list(self.bia.notificacoes.values_list("texto", flat=True))
        self.assertEqual(len(textos), 1)
        self.assertIn("vence amanhã", textos[0])

    def test_notificacao_abre_o_link_e_fica_lida(self):
        self.client.post(self.url("comentario_criar"), {"texto": "@bia veja"})
        notificacao = self.bia.notificacoes.get()
        self.client.login(username="bia", password="x")
        resposta = self.client.get(reverse("notificacoes:abrir", args=[notificacao.pk]))
        self.assertRedirects(resposta, self.url("item_detalhe"))
        notificacao.refresh_from_db()
        self.assertTrue(notificacao.lida)
