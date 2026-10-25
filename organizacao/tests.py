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
