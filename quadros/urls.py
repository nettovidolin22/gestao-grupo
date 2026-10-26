from django.urls import path

from . import views

app_name = "quadros"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("novo/", views.novo, name="novo"),
    path("importar/", views.importar, name="importar"),
    path("painel/", views.painel_gerencial, name="painel_gerencial"),
    path("<int:quadro_pk>/automacoes/", views.automacoes, name="automacoes"),
    path("<int:quadro_pk>/automacoes/<int:pk>/alternar/", views.automacao_alternar, name="automacao_alternar"),
    path("<int:quadro_pk>/automacoes/<int:pk>/excluir/", views.automacao_excluir, name="automacao_excluir"),
    path("<int:quadro_pk>/convidados/", views.convidados, name="convidados"),
    path("<int:quadro_pk>/convidados/<int:pk>/remover/", views.convidado_remover, name="convidado_remover"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/arquivar/", views.arquivar, name="arquivar"),
    path("<int:pk>/duplicar/", views.duplicar, name="duplicar"),
    path("<int:quadro_pk>/grupos/novo/", views.grupo_form, name="grupo_novo"),
    path("<int:quadro_pk>/grupos/<int:pk>/", views.grupo_form, name="grupo_editar"),
    path("<int:quadro_pk>/grupos/<int:pk>/excluir/", views.grupo_excluir, name="grupo_excluir"),
    path("<int:quadro_pk>/colunas/", views.colunas, name="colunas"),
    path("<int:quadro_pk>/colunas/nova/", views.coluna_form, name="coluna_nova"),
    path("<int:quadro_pk>/colunas/<int:pk>/", views.coluna_form, name="coluna_editar"),
    path("<int:quadro_pk>/colunas/<int:pk>/excluir/", views.coluna_excluir, name="coluna_excluir"),
    path("grupos/<int:grupo_pk>/itens/novo/", views.item_criar, name="item_criar"),
    path("itens/<int:pk>/nome/", views.item_nome, name="item_nome"),
    path("itens/<int:pk>/valor/<int:coluna_pk>/", views.item_valor, name="item_valor"),
    path("itens/<int:pk>/excluir/", views.item_excluir, name="item_excluir"),
    path("itens/<int:pk>/", views.item_detalhe, name="item_detalhe"),
    path("itens/<int:pk>/comentar/", views.comentario_criar, name="comentario_criar"),
    path("comentarios/<int:pk>/excluir/", views.comentario_excluir, name="comentario_excluir"),
    path("itens/<int:pk>/anexar/", views.anexo_enviar, name="anexo_enviar"),
    path("anexos/<int:pk>/", views.anexo_baixar, name="anexo_baixar"),
    path("anexos/<int:pk>/excluir/", views.anexo_excluir, name="anexo_excluir"),
    path("itens/<int:pk>/subtarefas/", views.subtarefa_criar, name="subtarefa_criar"),
    path("subtarefas/<int:pk>/alternar/", views.subtarefa_alternar, name="subtarefa_alternar"),
    path("subtarefas/<int:pk>/excluir/", views.subtarefa_excluir, name="subtarefa_excluir"),
]
