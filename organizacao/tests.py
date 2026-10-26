from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Empresa, Filial, Usuario

P = Usuario.Papel


class AcessoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alfa = Empresa.objects.create(nome="Alfa")
        cls.beta = Empresa.objects.create(nome="Beta")
        cls.matriz = Filial.objects.create(empresa=cls.alfa, nome="Matriz")
        cls.filial2 = Filial.objects.create(empresa=cls.alfa, nome="Filial 2")
        cls.beta_unica = Filial.objects.create(empresa=cls.beta, nome="Única")

    def criar(self, username, papel, empresa=None, filial=None):
        return Usuario.objects.create_user(
            username=username, password="x", papel=papel, empresa=empresa, filial=filial
        )

    def test_admin_do_grupo_ve_todas_as_filiais(self):
        u = self.criar("dir", P.ADMIN_GRUPO)
        self.assertEqual(u.filiais_visiveis().count(), 3)

    def test_gestor_de_empresa_ve_so_a_propria_empresa(self):
        u = self.criar("ge", P.GESTOR_EMPRESA, self.alfa)
        self.assertCountEqual(u.filiais_visiveis(), [self.matriz, self.filial2])

    def test_colaborador_ve_so_a_propria_filial(self):
        u = self.criar("col", P.COLABORADOR, self.alfa, self.filial2)
        self.assertCountEqual(u.filiais_visiveis(), [self.filial2])

    def test_filial_precisa_ser_da_empresa(self):
        u = Usuario(username="x", papel=P.COLABORADOR, empresa=self.alfa, filial=self.beta_unica)
        with self.assertRaises(ValidationError):
            u.clean()

    def test_colaborador_precisa_de_filial(self):
        u = Usuario(username="x", papel=P.COLABORADOR, empresa=self.alfa)
        with self.assertRaises(ValidationError):
            u.clean()

    def test_painel_exige_login(self):
        resposta = self.client.get(reverse("painel"))
        self.assertRedirects(resposta, f"{reverse('login')}?next=/")

    def test_painel_mostra_so_o_permitido(self):
        self.criar("col", P.COLABORADOR, self.alfa, self.filial2)
        self.client.login(username="col", password="x")
        resposta = self.client.get(reverse("painel"))
        self.assertContains(resposta, "Filial 2")
        self.assertNotContains(resposta, "Matriz")
        self.assertNotContains(resposta, "Beta")


class CadastroUsuariosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        P = Usuario.Papel
        cls.alfa = Empresa.objects.create(nome="Alfa")
        cls.beta = Empresa.objects.create(nome="Beta")
        cls.matriz = Filial.objects.create(empresa=cls.alfa, nome="Matriz")
        cls.f2 = Filial.objects.create(empresa=cls.alfa, nome="Filial 2")
        cls.fb = Filial.objects.create(empresa=cls.beta, nome="Única")
        cls.admin = Usuario.objects.create_user("admin", password="x", papel=P.ADMIN_GRUPO)
        cls.gestor = Usuario.objects.create_user("gestor", password="x", papel=P.GESTOR_EMPRESA, empresa=cls.alfa)
        cls.gfilial = Usuario.objects.create_user("gfilial", password="x", papel=P.GESTOR_FILIAL, empresa=cls.alfa, filial=cls.matriz)
        cls.colab = Usuario.objects.create_user("colab", password="x", papel=P.COLABORADOR, empresa=cls.alfa, filial=cls.matriz)
        cls.outro = Usuario.objects.create_user("outro", password="x", papel=P.COLABORADOR, empresa=cls.beta, filial=cls.fb)

    def dados(self, **extra):
        base = {"first_name": "Ana", "username": "ana", "email": "ana@x.com", "papel": "colaborador",
                "empresa": self.alfa.pk, "filial": self.matriz.pk, "is_active": "on",
                "senha1": "Senha-forte-2026", "senha2": "Senha-forte-2026"}
        base.update(extra)
        return base

    def test_colaborador_nao_acessa(self):
        self.client.force_login(self.colab)
        self.assertEqual(self.client.get(reverse("usuarios")).status_code, 403)

    def test_gestor_ve_so_usuarios_da_empresa(self):
        self.client.force_login(self.gestor)
        resposta = self.client.get(reverse("usuarios"))
        self.assertContains(resposta, "colab")
        self.assertNotContains(resposta, "outro")
        self.assertEqual(self.client.get(reverse("usuario_editar", args=[self.outro.pk])).status_code, 404)

    def test_gestor_cadastra_colaborador_que_consegue_entrar(self):
        self.client.force_login(self.gestor)
        resposta = self.client.post(reverse("usuario_novo"), self.dados())
        self.assertRedirects(resposta, reverse("usuarios"))
        ana = Usuario.objects.get(username="ana")
        self.assertEqual(ana.filial, self.matriz)
        self.assertTrue(self.client.login(username="ana", password="Senha-forte-2026"))

    def test_gestor_nao_cria_administrador_nem_usuario_em_outra_empresa(self):
        self.client.force_login(self.gestor)
        self.client.post(reverse("usuario_novo"), self.dados(papel="admin_grupo"))
        self.client.post(reverse("usuario_novo"), self.dados(username="bia", empresa=self.beta.pk, filial=self.fb.pk))
        self.assertFalse(Usuario.objects.filter(username__in=["ana", "bia"], papel="admin_grupo").exists())
        self.assertFalse(Usuario.objects.filter(username="bia", empresa=self.beta).exists())

    def test_gestor_de_filial_cadastra_so_na_propria_filial(self):
        self.client.force_login(self.gfilial)
        self.client.post(reverse("usuario_novo"), self.dados(filial=self.f2.pk))
        ana = Usuario.objects.get(username="ana")
        self.assertEqual(ana.filial, self.matriz)
        self.assertEqual(ana.papel, "colaborador")

    def test_senha_fraca_recusada(self):
        self.client.force_login(self.gestor)
        resposta = self.client.post(reverse("usuario_novo"), self.dados(senha1="123", senha2="123"))
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(username="ana").exists())

    def test_desativar_bloqueia_login(self):
        self.client.force_login(self.gestor)
        self.client.post(reverse("usuario_editar", args=[self.colab.pk]), {
            "first_name": "", "username": "colab", "email": "", "papel": "colaborador",
            "empresa": self.alfa.pk, "filial": self.matriz.pk,
        })
        self.colab.refresh_from_db()
        self.assertFalse(self.colab.is_active)

    def test_redefinir_senha(self):
        self.client.force_login(self.gestor)
        self.client.post(reverse("usuario_senha", args=[self.colab.pk]),
                         {"new_password1": "Outra-senha-77", "new_password2": "Outra-senha-77"})
        self.client.logout()
        self.assertTrue(self.client.login(username="colab", password="Outra-senha-77"))

    def test_admin_do_grupo_criado_aqui_entra_em_cadastros(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("usuario_novo"), self.dados(papel="admin_grupo", empresa="", filial=""))
        self.assertTrue(Usuario.objects.get(username="ana").is_staff)
