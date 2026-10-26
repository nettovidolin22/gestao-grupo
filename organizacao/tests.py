from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
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


@override_settings(DOMINIOS_EMAIL=[])
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

    def test_so_administrador_acessa(self):
        for quem in (self.colab, self.gfilial, self.gestor):
            self.client.force_login(quem)
            self.assertEqual(self.client.get(reverse("usuarios")).status_code, 403)
            self.assertEqual(self.client.post(reverse("usuario_novo"), self.dados()).status_code, 403)
        self.assertFalse(Usuario.objects.filter(username="ana").exists())

    def test_administrador_cadastra_usuario_que_consegue_entrar(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse("usuario_novo"), self.dados())
        self.assertRedirects(resposta, reverse("usuarios"))
        ana = Usuario.objects.get(username="ana")
        self.assertEqual(ana.filial, self.matriz)
        self.client.logout()
        self.assertTrue(self.client.login(username="ana", password="Senha-forte-2026"))

    def test_entra_com_email_corporativo(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("usuario_novo"), self.dados())
        self.client.logout()
        resposta = self.client.post(reverse("login"), {"username": "ANA@x.com", "password": "Senha-forte-2026"})
        self.assertEqual(resposta.status_code, 302)

    def test_email_repetido_recusado(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("usuario_novo"), self.dados())
        self.client.post(reverse("usuario_novo"), self.dados(username="ana2"))
        self.assertFalse(Usuario.objects.filter(username="ana2").exists())

    @override_settings(DOMINIOS_EMAIL=["gencau.com", "balaiolab.com", "titan.ind.br"])
    def test_so_aceita_dominio_corporativo(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("usuario_novo"), self.dados(email="ana@gmail.com"))
        self.assertFalse(Usuario.objects.filter(username="ana").exists())
        self.client.post(reverse("usuario_novo"), self.dados(email="ana@titan.ind.br"))
        self.assertTrue(Usuario.objects.filter(username="ana").exists())

    def test_senha_fraca_recusada(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse("usuario_novo"), self.dados(senha1="123", senha2="123"))
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(username="ana").exists())

    def test_desativar_bloqueia_login(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("usuario_editar", args=[self.colab.pk]), {
            "first_name": "", "username": "colab", "email": "colab@x.com", "papel": "colaborador",
            "empresa": self.alfa.pk, "filial": self.matriz.pk,
        })
        self.colab.refresh_from_db()
        self.assertFalse(self.colab.is_active)

    def test_redefinir_senha(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("usuario_senha", args=[self.colab.pk]),
                         {"new_password1": "Outra-senha-77", "new_password2": "Outra-senha-77"})
        self.client.logout()
        self.assertTrue(self.client.login(username="colab", password="Outra-senha-77"))

    def test_admin_do_grupo_criado_aqui_entra_em_cadastros(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("usuario_novo"), self.dados(papel="admin_grupo", empresa="", filial=""))
        self.assertTrue(Usuario.objects.get(username="ana").is_staff)
