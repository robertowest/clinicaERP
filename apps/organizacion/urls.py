"""urls html de organizacion: listados + formularios/confirmaciones en modal o página
completa (clínica)."""

from django.urls import path

from apps.organizacion import views

app_name = 'organizacion'

urlpatterns = [
    # grupos
    path('grupos/', views.GrupoListView.as_view(), name='grupo-list'),
    path('grupos/nuevo/', views.GrupoCreateView.as_view(), name='grupo-crear'),
    path('grupos/<int:pk>/', views.GrupoDetalleView.as_view(), name='grupo-detalle'),
    path('grupos/<int:pk>/editar/', views.GrupoUpdateView.as_view(), name='grupo-editar'),
    path('grupos/<int:pk>/eliminar/', views.GrupoBajaView.as_view(), name='grupo-eliminar'),
    path('grupos/<int:pk>/reactivar/', views.GrupoReactivarView.as_view(), name='grupo-reactivar'),

    # clínicas
    path('clinicas/', views.ClinicaListView.as_view(), name='clinica-list'),
    path('clinicas/nueva/', views.ClinicaCreateView.as_view(), name='clinica-crear'),
    path('clinicas/<int:pk>/', views.ClinicaDetalleView.as_view(), name='clinica-detalle'),
    path('clinicas/<int:pk>/editar/', views.ClinicaUpdateView.as_view(), name='clinica-editar'),
    path('clinicas/<int:pk>/eliminar/', views.ClinicaBajaView.as_view(), name='clinica-eliminar'),
    path('clinicas/<int:pk>/reactivar/', views.ClinicaReactivarView.as_view(), name='clinica-reactivar'),

    # especialidades
    path('especialidades/', views.EspecialidadListView.as_view(), name='especialidad-list'),
    path('especialidades/nueva/', views.EspecialidadCreateView.as_view(), name='especialidad-crear'),
    path('especialidades/<int:pk>/', views.EspecialidadDetalleView.as_view(), name='especialidad-detalle'),
    path('especialidades/<int:pk>/editar/', views.EspecialidadUpdateView.as_view(), name='especialidad-editar'),
    path('especialidades/<int:pk>/eliminar/',views.EspecialidadBajaView.as_view(),name='especialidad-eliminar'),
    path('especialidades/<int:pk>/reactivar/',views.EspecialidadReactivarView.as_view(),name='especialidad-reactivar'),
]
