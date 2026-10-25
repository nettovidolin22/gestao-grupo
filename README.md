# Gestão do Grupo

Sistema de gestão de tarefas e projetos para o grupo (empresas, filiais e equipes), feito em Python com Django.

## O que já existe (módulo 1)

- Login, logout e troca de senha
- Cadastro de empresas, filiais e usuários (tela **Cadastros**, em `/admin`)
- Perfis de acesso:
  - **Administrador do grupo:** vê tudo
  - **Gestor de empresa:** vê todas as filiais da própria empresa
  - **Gestor de filial** e **Colaborador:** veem só a própria filial
- Painel inicial mostrando as empresas e filiais que o usuário pode acessar

A regra de acesso fica em `Usuario.filiais_visiveis()` (`organizacao/models.py`). Toda tela nova deve filtrar os dados por ela.

## Rodar no seu computador (Windows)

No VS Code, abra a pasta do projeto e use o terminal (menu **Terminal > Novo Terminal**):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py dados_exemplo
python manage.py createsuperuser
python manage.py runserver
```

Abra http://127.0.0.1:8000 no navegador.

- `dados_exemplo` cria 3 empresas, filiais e 4 usuários de teste (`diretoria`, `gestor.alfa`, `gestor.matriz`, `colaborador`, senha `teste12345`). Entre com cada um para ver a diferença de acesso.
- `createsuperuser` cria o seu usuário de administrador, que acessa a tela **Cadastros**.

Se o PowerShell bloquear o `activate`, rode antes: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Testes

```powershell
python manage.py test
```

## Banco de dados

Sem configuração, o sistema usa um arquivo SQLite local (`db.sqlite3`). Para usar o Supabase, pegue a connection string em **Project Settings > Database** e coloque em `DATABASE_URL` no arquivo `.env`.

## Estrutura

| Pasta | O que tem |
| --- | --- |
| `config/` | Configurações e endereços (URLs) do projeto |
| `organizacao/` | Empresas, filiais, usuários e permissões |
| `templates/` | As telas (HTML) |
| `static/css/` | O visual |
