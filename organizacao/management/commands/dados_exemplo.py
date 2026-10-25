from django.core.management.base import BaseCommand

from organizacao.models import Empresa, Filial, Usuario

SENHA = "teste12345"


class Command(BaseCommand):
    help = "Cria empresas, filiais e usuários de exemplo para testar o sistema."

    def handle(self, *args, **options):
        alfa, _ = Empresa.objects.get_or_create(nome="Empresa Alfa")
        beta, _ = Empresa.objects.get_or_create(nome="Empresa Beta")
        gama, _ = Empresa.objects.get_or_create(nome="Empresa Gama")
        filiais = {}
        for nome in ["Matriz", "Filial 2", "Filial 3", "Filial 4"]:
            filiais[nome], _ = Filial.objects.get_or_create(empresa=alfa, nome=nome, defaults={"cidade": "Tambaú"})
        Filial.objects.get_or_create(empresa=beta, nome="Única")
        Filial.objects.get_or_create(empresa=gama, nome="Única")

        P = Usuario.Papel
        usuarios = [
            ("diretoria", P.ADMIN_GRUPO, None, None),
            ("gestor.alfa", P.GESTOR_EMPRESA, alfa, None),
            ("gestor.matriz", P.GESTOR_FILIAL, alfa, filiais["Matriz"]),
            ("colaborador", P.COLABORADOR, alfa, filiais["Filial 2"]),
        ]
        for username, papel, empresa, filial in usuarios:
            usuario, criado = Usuario.objects.get_or_create(
                username=username, defaults={"papel": papel, "empresa": empresa, "filial": filial}
            )
            if criado:
                usuario.set_password(SENHA)
                usuario.save()
        self.stdout.write(self.style.SUCCESS(
            f"Pronto. Usuários: diretoria, gestor.alfa, gestor.matriz, colaborador. Senha: {SENHA}"
        ))
