"""
filtros django-filter de medicos
declaran Meta.model por diseño de la librería
(excepción permitida a acceso directo al modelo, ver arquitectura.md §5).
"""
import django_filters
from django_filters.widgets import BooleanWidget

from apps.medicos.models import Medico

# is_active parte de BooleanWidget (no forms.Select) para conservar sus choices
# Desconocido/Sí/No, mismo criterio que apps/pacientes/filters.py.
WIDGET_ESTADO = BooleanWidget(attrs={'style': 'max-width: 140px'})


class MedicoFilter(django_filters.FilterSet):
    # nombre/apellido no son campos propios de Medico: se leen de usuario.
    nombre = django_filters.CharFilter(
        field_name='usuario__first_name', label='Nombre', lookup_expr='icontains',
    )
    apellido = django_filters.CharFilter(
        field_name='usuario__last_name', label='Apellido', lookup_expr='icontains',
    )
    colegiado = django_filters.CharFilter(label='Colegiado', lookup_expr='icontains')
    is_active = django_filters.BooleanFilter(widget=WIDGET_ESTADO)

    class Meta:
        model = Medico
        fields = ['nombre', 'apellido', 'colegiado', 'is_active']
