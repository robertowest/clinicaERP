"""filtros django-filter de pacientes; declaran Meta.model por diseño de la librería
(excepción permitida a acceso directo al modelo, ver arquitectura.md §5)."""
import django_filters
from django import forms
from django_filters.widgets import BooleanWidget

from apps.pacientes.models import Paciente

# is_active parte de BooleanWidget (no forms.Select) para conservar sus choices
# Desconocido/Sí/No, mismo criterio que apps/organizacion/filters.py.
WIDGET_ESTADO = BooleanWidget(attrs={'style': 'max-width: 140px'})
WIDGET_TEXTO =  forms.TextInput(attrs={'style': 'max-width: 140px'})


class PacienteFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(label='Nombre', lookup_expr='icontains')
    apellido = django_filters.CharFilter(label='Apellido', lookup_expr='icontains')
    nhc = django_filters.CharFilter(label='NHC', lookup_expr='icontains', widget=WIDGET_TEXTO)
    documento_numero = django_filters.CharFilter(label='Documento', lookup_expr='icontains', widget=WIDGET_TEXTO)
    is_active = django_filters.BooleanFilter(widget=WIDGET_ESTADO)

    class Meta:
        model = Paciente
        fields = [
            'nombre', 'apellido', 'nhc', 'documento_numero', 'sexo', 'is_active',
        ]
