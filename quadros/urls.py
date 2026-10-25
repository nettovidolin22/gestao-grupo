from django.urls import path

from . import views

app_name = "quadros"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("novo/", views.novo, name="novo"),
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
]
