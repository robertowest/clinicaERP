"""urls html de usuarios: listado + formulario en página completa, y gestión de
accesos por clínica (alta/baja de rol) en su propia página."""

from django.urls import path

from apps.usuarios import views

app_name = 'usuarios'

urlpatterns = [
    # dashboards por rol
    path('recepcion-dashboard/', views.RecepcionDashboardView.as_view(), name='recepcion-dashboard'),

    # gestión de usuarios
    path('', views.UsuarioListView.as_view(), name='usuario-list'),
    path('nuevo/', views.UsuarioCreateView.as_view(), name='usuario-crear'),
    path('<int:pk>/', views.UsuarioDetalleView.as_view(), name='usuario-detalle'),
    path('<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario-editar'),
    path('<int:pk>/eliminar/', views.UsuarioBajaView.as_view(), name='usuario-eliminar'),
    path('<int:pk>/reactivar/', views.UsuarioReactivarView.as_view(), name='usuario-reactivar'),

    # accesos por clínica (UsuarioClinica)
    path('<int:usuario_pk>/accesos/', views.UsuarioAccesosView.as_view(), name='usuario-accesos'),
    path('<int:usuario_pk>/accesos/nuevo/', views.UsuarioAccesoCrearView.as_view(), name='usuario-acceso-crear'),
    path('<int:usuario_pk>/accesos/<int:pk>/eliminar/', views.UsuarioAccesoEliminarView.as_view(), name='usuario-acceso-eliminar'),
]
