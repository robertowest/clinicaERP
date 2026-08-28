"""urls html de pacientes: listado + formulario en página completa + detalle/baja en modal."""

from django.urls import path

from apps.pacientes import views

app_name = 'pacientes'

urlpatterns = [
    path('', views.PacienteListView.as_view(), name='paciente-list'),
    path('nuevo/', views.PacienteCreateView.as_view(), name='paciente-crear'),
    path('<int:pk>/', views.PacienteDetalleView.as_view(), name='paciente-detalle'),
    path('<int:pk>/editar/', views.PacienteUpdateView.as_view(), name='paciente-editar'),
    path('<int:pk>/eliminar/', views.PacienteBajaView.as_view(), name='paciente-eliminar'),
    path('<int:pk>/reactivar/', views.PacienteReactivarView.as_view(), name='paciente-reactivar'),
]
