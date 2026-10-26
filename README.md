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

## Módulo 3: visualizações

- Abas **Tabela**, **Kanban** e **Calendário** em cada quadro
- Kanban: cartões agrupados por uma coluna de Status (escolha qual em "Agrupar por"). Arraste um cartão para outra coluna, ou use o seletor no cartão pelo celular, e o status muda na hora
- Calendário: itens posicionados no mês pela coluna de Data, coloridos pelo status, com navegação entre meses e lista dos itens sem data

## Módulo 4: colaboração

- Página de cada item (botão ↗ na tabela, ou clique no cartão do Kanban ou no calendário) com os campos, subtarefas, comentários, anexos e histórico
- Comentários com menção: escreva `@usuario` para avisar alguém que vê o quadro
- Anexos de até 10 MB, baixados só por quem tem acesso ao item
- Histórico automático: quem criou, renomeou, mudou um campo, comentou ou anexou, e quando
- Notificações no sistema (menu **Notificações**) e por e-mail quando alguém é atribuído, mencionado ou recebe comentário num item seu
- Aviso de prazo: `python manage.py avisar_prazos` avisa quem tem item vencendo amanhã ou que venceu ontem (itens com status Feito ficam de fora). Em produção ele roda uma vez por dia, agendado

Sem `EMAIL_HOST` no `.env`, os e-mails aparecem no terminal em vez de serem enviados.

## Módulo 5: gestão

- **Automações** por quadro (botão Automações): quando uma coluna de Status mudar para uma etiqueta, avisar uma pessoa, avisar os responsáveis ou mover o item para outro grupo. Dá para pausar e excluir
- **Painel gerencial** (menu Painel, só gestores): itens em aberto, concluídos, atrasados e que vencem em 7 dias, com quebra por filial, por responsável e a lista dos atrasados. Filtro por empresa e filial
- **Importar do Monday** (na lista de quadros): envie o Excel exportado do Monday (ou um CSV). Cada grupo vira um grupo, e o tipo de cada coluna (Status, Pessoa, Data, Número, Texto) é adivinhado pelos valores. Pessoas são reconhecidas pelo nome completo ou usuário

Os valores de cada item ficam em `Item.valores`, um JSON com o id da coluna como chave. A validação de cada tipo está em `Coluna.limpar_valor()` (`quadros/models.py`).

A regra de acesso fica em `Usuario.filiais_visiveis()` (`organizacao/models.py`). Toda tela nova deve filtrar os dados por ela.

## Usuários

Menu **Usuários**, só para o administrador do grupo (TI): lista com busca, cadastro com senha inicial, edição, bloqueio (desmarcar Ativo) e nova senha. Ninguém edita a si mesmo por essa tela.

- O e-mail é obrigatório, único e também serve para entrar no sistema
- Só são aceitos e-mails @gencau.com, @balaiolab.com e @titan.ind.br (mude em `DOMINIOS_EMAIL` no `.env`)

## Convidados (tarefas entre filiais e empresas)

- No quadro, o gestor da filial clica em **Convidados** e escolhe qualquer pessoa ativa do grupo, de outra filial ou empresa.
- O convidado recebe um aviso (no sistema e por e-mail), vê o quadro inteiro e pode receber tarefas, comentar, anexar e mudar status.
- Ele não mexe na estrutura: grupos, colunas, automações, convidados, editar, duplicar ou arquivar continuam com os gestores da filial dona do quadro.
- Na lista de quadros, o quadro aparece com a marca “convidado”. O painel gerencial só conta os quadros da própria área.
- Remover o convidado tira o acesso na hora.

## Segurança

- Depois de 5 senhas erradas seguidas, o usuário fica bloqueado por 15 minutos
- A sessão expira após 12 horas sem uso
- A tela **Cadastros** é só do administrador do grupo; gestores não entram nela
- Colaborador só exclui itens que ele mesmo criou; gestores excluem qualquer um
- Envios acima de 11 MB são recusados na entrada; o importador limita linhas, colunas e o tamanho descompactado do Excel
- Sem `DEBUG=1`, o sistema exige uma `SECRET_KEY` de 50+ caracteres, força HTTPS (com HSTS) e usa cookies seguros
- `dados_exemplo` (senhas fracas) só roda com `DEBUG=1`

## Antes de publicar

- Anexos ficam na pasta `MEDIA_ROOT`. Em hospedagem com disco temporário (como o Render), aponte `MEDIA_ROOT` para um disco persistente, senão os anexos somem a cada atualização.
- Defina `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`, `SITE_URL` e o e-mail (`EMAIL_HOST` e afins) no ambiente.
- Agende `python manage.py avisar_prazos` uma vez por dia.

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
