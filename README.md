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

## Módulo 2: quadros

- Quadros por filial, criados por gestores, já com o grupo "Tarefas" e as colunas Status, Responsável, Prazo e Prioridade
- Grupos de itens com cor, colunas personalizáveis (Texto, Número, Status com etiquetas coloridas, Pessoa, Data)
- Edição direto na tabela: mudou o valor, salvou (usa [htmx](https://htmx.org), guardado em `static/js`)
- Duplicar quadro (com ou sem itens) para usar como modelo, e arquivar quadro
- Colaboradores criam e editam itens; só gestores mudam quadros, grupos e colunas

Os valores de cada item ficam em `Item.valores`, um JSON com o id da coluna como chave. A validação de cada tipo está em `Coluna.limpar_valor()` (`quadros/models.py`).

A regra de acesso fica em `Usuario.filiais_visiveis()` (`organizacao/models.py`). Toda tela nova deve filtrar os dados por ela.

## Rodar no seu computador (Windows)

No VS Code, abra a pasta do projeto e use o terminal (menu **Terminal > Novo Terminal**):

```powershell
py -m venv .venv
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

Se o comando `python` abrir a Microsoft Store, use `py` para criar a `.venv`; depois de ativada, `python` funciona.

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
