from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from organizacao.models import Empresa, Filial, Usuario
from quadros.models import Quadro

SENHA = "teste12345"


class Command(BaseCommand):
    help = "Cria empresas, filiais e usuários de exemplo para testar o sistema."

    def add_arguments(self, parser):
        parser.add_argument(
            "--forcar", action="store_true",
            help="Roda mesmo fora do modo de testes (DEBUG desligado). Cuidado: cria senhas fracas.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["forcar"]:
            raise CommandError(
                "Este comando cria usuários com senha fraca e só roda com DEBUG=1 (computador local)."
            )
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
        if not Quadro.objects.filter(nome="Manutenção", filial=filiais["Matriz"]).exists():
            quadro = Quadro.criar_padrao(nome="Manutenção", filial=filiais["Matriz"])
            status, responsavel, prazo, prioridade = quadro.colunas.all()
            grupo = quadro.grupos.first()
            gestor = Usuario.objects.get(username="gestor.matriz")
            exemplos = [
                ("Trocar lâmpadas do galpão", "Feito", "Baixa"),
                ("Revisar extintores", "Fazendo", "Alta"),
                ("Orçamento do ar-condicionado", "A fazer", "Média"),
            ]
            for nome, st, pr in exemplos:
                item = grupo.itens.create(nome=nome)
                item.definir_valor(status, st)
                item.definir_valor(prioridade, pr)
                item.definir_valor(responsavel, str(gestor.pk))
                item.definir_valor(prazo, "2026-11-30")
        self.stdout.write(self.style.SUCCESS(
            f"Pronto. Usuários: diretoria, gestor.alfa, gestor.matriz, colaborador. Senha: {SENHA}"
        ))
