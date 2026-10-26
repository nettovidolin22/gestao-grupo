"""Testes das correções da revisão de segurança."""

import io
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from organizacao.models import Empresa, Filial, TentativaLogin, Usuario

from .importacao import ErroImportacao, ler_linhas
from .models import Automacao, Quadro

P = Usuario.Papel


class SegurancaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        alfa = Empresa.objects.create(nome="Alfa")
        cls.matriz = Filial.objects.create(empresa=alfa, nome="Matriz")
        cls.filial2 = Filial.objects.create(empresa=alfa, nome="Filial 2")
        cls.gestor = Usuario.objects.create_user(
            "gestor", password="senha-boa-123", papel=P.GESTOR_EMPRESA, empresa=alfa, is_staff=True
        )
        cls.colab = Usuario.objects.create_user(
            "colab", password="x", papel=P.COLABORADOR, empresa=alfa, filial=cls.matriz
        )
        cls.admin = Usuario.objects.create_user(
            "diretoria", password="x", papel=P.ADMIN_GRUPO, is_staff=True
        )
        cls.quadro = Quadro.criar_padrao(nome="Manutenção", filial=cls.matriz)
        cls.grupo = cls.quadro.grupos.first()

    def entrar(self, username, senha):
        return self.client.post(reverse("login"), {"username": username, "password": senha})

    def test_login_bloqueia_depois_de_cinco_erros(self):
        for _ in range(5):
            self.entrar("gestor", "errada")
        resposta = self.entrar("gestor", "senha-boa-123")
        self.assertContains(resposta, "Muitas tentativas erradas")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_certo_zera_as_tentativas(self):
        self.entrar("gestor", "errada")
        resposta = self.entrar("gestor", "senha-boa-123")
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(TentativaLogin.objects.filter(username="gestor").exists())

    def test_cadastros_so_para_administrador_do_grupo(self):
        self.client.force_login(self.gestor)  # é staff, mas não é admin do grupo
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        # Administrador do grupo sem ser superusuário consegue cadastrar usuários.
        self.assertEqual(self.client.get("/admin/organizacao/usuario/add/").status_code, 200)

    def test_colaborador_nao_exclui_item_de_outra_pessoa(self):
        item = self.grupo.itens.create(nome="Do gestor", criado_por=self.gestor)
        meu = self.grupo.itens.create(nome="Meu", criado_por=self.colab)
        self.client.force_login(self.colab)
        resposta = self.client.post(reverse("quadros:item_excluir", args=[item.pk]))
        self.assertEqual(resposta.status_code, 403)
        self.client.post(reverse("quadros:item_excluir", args=[meu.pk]))
        self.assertFalse(self.grupo.itens.filter(pk=meu.pk).exists())

    def test_pessoa_com_texto_invalido_nao_quebra(self):
        item = self.grupo.itens.create(nome="X")
        pessoa = self.quadro.colunas.get(nome="Responsável")
        self.client.force_login(self.colab)
        resposta = self.client.post(
            reverse("quadros:item_valor", args=[item.pk, pessoa.pk]), {"valor": "abc"}
        )
        self.assertEqual(resposta.status_code, 302)

    def test_painel_e_calendario_com_parametros_invalidos(self):
        self.client.force_login(self.gestor)
        resposta = self.client.get(reverse("quadros:painel_gerencial"), {"empresa": "x", "filial": "1;"})
        self.assertEqual(resposta.status_code, 200)
        resposta = self.client.get(
            reverse("quadros:detalhe", args=[self.quadro.pk]), {"visao": "calendario", "mes": "0001-01"}
        )
        self.assertEqual(resposta.status_code, 200)

    @override_settings(TAMANHO_MAXIMO_REQUISICAO=100)
    def test_envio_gigante_recusado_na_entrada(self):
        item = self.grupo.itens.create(nome="X")
        self.client.force_login(self.colab)
        arquivo = SimpleUploadedFile("grande.bin", b"0" * 500)
        resposta = self.client.post(reverse("quadros:anexo_enviar", args=[item.pk]), {"arquivo": arquivo})
        self.assertEqual(resposta.status_code, 413)

    def test_excel_bomba_de_zip_recusado(self):
        conteudo = io.BytesIO()
        with zipfile.ZipFile(conteudo, "w", zipfile.ZIP_DEFLATED) as pacote:
            pacote.writestr("xl/sharedStrings.xml", "a" * (60 * 1024 * 1024))
        arquivo = SimpleUploadedFile("bomba.xlsx", conteudo.getvalue())
        with self.assertRaisesMessage(ErroImportacao, "grande demais"):
            ler_linhas(arquivo)

    def test_csv_com_linhas_demais_recusado(self):
        arquivo = SimpleUploadedFile("muito.csv", ("Nome\n" + "a\n" * 6000).encode())
        with self.assertRaisesMessage(ErroImportacao, "mais de 5000"):
            ler_linhas(arquivo)

    def test_automacao_nao_avisa_quem_saiu_da_filial(self):
        status = self.quadro.colunas.get(nome="Status")
        Automacao.objects.create(
            quadro=self.quadro, coluna=status, valor="Feito",
            acao=Automacao.Acao.AVISAR_PESSOA, pessoa=self.colab,
        )
        self.colab.filial = self.filial2
        self.colab.save()
        item = self.grupo.itens.create(nome="X")
        self.client.force_login(self.gestor)
        self.client.post(reverse("quadros:item_valor", args=[item.pk, status.pk]), {"valor": "Feito"})
        self.assertFalse(self.colab.notificacoes.exists())

    @override_settings(DEBUG=False)
    def test_dados_exemplo_nao_roda_em_producao(self):
        from django.core.management import CommandError, call_command

        with self.assertRaises(CommandError):
            call_command("dados_exemplo")

    def test_nome_com_quebra_de_linha_ainda_manda_email(self):
        from django.core import mail

        from notificacoes.servicos import notificar

        self.colab.email = "colab@exemplo.com"
        self.colab.save()
        notificar(self.colab, "Item\ncom quebra", autor=self.gestor)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("\n", mail.outbox[0].subject)
