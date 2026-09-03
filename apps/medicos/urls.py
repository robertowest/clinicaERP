"""urls html de medicos: listado + formulario en página completa + detalle/baja en modal,
y gestión de especialidad por clínica (MedicoClinicaEspecialidad) en su propia página."""

from django.urls import path

from apps.medicos import views

app_name = 'medicos'

urlpatterns = [
    # dashboards por rol
    path('dashboard/', views.MedicoDashboardView.as_view(), name='dashboard'),

    # gestión de médicos
    path('', views.MedicoListView.as_view(), name='medico-list'),
    path('nuevo/', views.MedicoCreateView.as_view(), name='medico-crear'),
    path('<int:pk>/', views.MedicoDetalleView.as_view(), name='medico-detalle'),
    path('<int:pk>/editar/', views.MedicoUpdateView.as_view(), name='medico-editar'),
    path('<int:pk>/eliminar/', views.MedicoBajaView.as_view(), name='medico-eliminar'),
    path('<int:pk>/reactivar/', views.MedicoReactivarView.as_view(), name='medico-reactivar'),

    # especialidad por clínica (MedicoClinicaEspecialidad)
    path('<int:medico_pk>/clinicas/', views.MedicoClinicasView.as_view(), name='medico-clinicas'),
    path('<int:medico_pk>/clinicas/nuevo/', views.MedicoClinicaCrearView.as_view(), name='medico-clinica-crear'),
    path('<int:medico_pk>/clinicas/<int:pk>/eliminar/', views.MedicoClinicaEliminarView.as_view(), name='medico-clinica-eliminar'),

    # ausencias (MedicoAusencia)
    path('ausencias/', views.AusenciaListView.as_view(), name='ausencia-list'),
    path('ausencias/nueva/', views.AusenciaCreateView.as_view(), name='ausencia-crear'),
    path('ausencias/<int:pk>/', views.AusenciaDetalleView.as_view(), name='ausencia-detalle'),
    path('ausencias/<int:pk>/editar/', views.AusenciaUpdateView.as_view(), name='ausencia-editar'),
    path('ausencias/<int:pk>/eliminar/', views.AusenciaBajaView.as_view(), name='ausencia-eliminar'),
    path('ausencias/<int:pk>/reactivar/', views.AusenciaReactivarView.as_view(), name='ausencia-reactivar'),
]
