"""Testes da varredura final antes da junção dos módulos."""

import os
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.uploadhandler import StopUpload
from django.test import TestCase, override_settings
from django.urls import reverse

from config.uploads import LimiteUpload
from organizacao.models import Empresa, Filial, Usuario

from .models import Coluna, Item, Quadro

P = Usuario.Papel


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RevisaoFinalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        gencau = Empresa.objects.create(nome="Gencau")
        cls.matriz = Filial.objects.create(empresa=gencau, nome="Matriz")
        cls.gestor = Usuario.objects.create_user(
            "gestor", password="x", papel=P.GESTOR_FILIAL, empresa=gencau, filial=cls.matriz
        )
        cls.ti = Usuario.objects.create_user("ti", password="x", papel=P.ADMIN_GRUPO, is_staff=True)
        cls.root = Usuario.objects.create_superuser("root", password="x")
        cls.quadro = Quadro.criar_padrao(nome="Compras", filial=cls.matriz)
        cls.grupo = cls.quadro.grupos.first()

    def test_numero_nao_aceita_nan_nem_infinito(self):
        coluna = self.quadro.colunas.create(nome="Valor", tipo=Coluna.Tipo.NUMERO)
        item = self.grupo.itens.create(nome="X")
        self.client.force_login(self.gestor)
        for texto in ("NaN", "Infinity", "-inf"):
            self.client.post(reverse("quadros:item_valor", args=[item.pk, coluna.pk]), {"valor": texto})
            item.refresh_from_db()
            self.assertIsNone(item.valor(coluna))

    def test_mudancas_simultaneas_em_colunas_diferentes_nao_se_perdem(self):
        status = self.quadro.colunas.get(nome="Status")
        prazo = self.quadro.colunas.get(nome="Prazo")
        item = self.grupo.itens.create(nome="X")
        desatualizado = Item.objects.get(pk=item.pk)  # tela de outra pessoa, aberta antes
        item.definir_valor(status, "Feito")
        desatualizado.definir_valor(prazo, "2026-12-01")
        item.refresh_from_db()
        self.assertEqual(item.valor(status), "Feito")
        self.assertEqual(item.valor(prazo), "2026-12-01")

    def test_excluir_item_apaga_o_arquivo_do_anexo(self):
        item = self.grupo.itens.create(nome="X", criado_por=self.gestor)
        self.client.force_login(self.gestor)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("quadros:anexo_enviar", args=[item.pk]),
                {"arquivo": SimpleUploadedFile("nota.pdf", b"conteudo")},
            )
        caminho = item.anexos.get().arquivo.path
        self.assertTrue(os.path.exists(caminho))
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("quadros:item_excluir", args=[item.pk]))
        self.assertFalse(os.path.exists(caminho))

    @override_settings(TAMANHO_MAXIMO_REQUISICAO=10)
    def test_envio_sem_tamanho_declarado_e_interrompido(self):
        limite = LimiteUpload()
        limite.receive_data_chunk(b"12345", 0)
        with self.assertRaises(StopUpload):
            limite.receive_data_chunk(b"678901", 5)

    def test_administrador_do_grupo_nao_mexe_em_superusuario_nos_cadastros(self):
        self.client.force_login(self.ti)
        url = reverse("admin:organizacao_usuario_change", args=[self.root.pk])
        self.assertNotEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.root)
        self.assertEqual(self.client.get(url).status_code, 200)

    @override_settings(DOMINIOS_EMAIL=["gencau.com"])
    def test_cadastros_tambem_exige_email_corporativo(self):
        self.client.force_login(self.ti)
        url = reverse("admin:organizacao_usuario_change", args=[self.gestor.pk])
        resposta = self.client.get(url)
        dados = {
            k: v for k, v in resposta.context["adminform"].form.initial.items()
            if v is not None and k not in ("password", "last_login", "date_joined", "groups", "user_permissions")
        }
        dados.update(email="gestor@gmail.com", empresa=self.matriz.empresa_id, filial=self.matriz.pk)
        self.client.post(url, dados)
        self.gestor.refresh_from_db()
        self.assertEqual(self.gestor.email, "")
        dados["email"] = "Gestor@Gencau.com"
        self.client.post(url, dados)
        self.gestor.refresh_from_db()
        self.assertEqual(self.gestor.email, "gestor@gencau.com")
