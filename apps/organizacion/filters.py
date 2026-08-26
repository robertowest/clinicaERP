"""filtros django-filter de organizacion; declaran Meta.model por diseño de la librería
(excepción permitida a acceso directo al modelo, ver arquitectura.md §5)."""
import django_filters
from django import forms
from django_filters.widgets import BooleanWidget

from apps.organizacion.models import Clinica, Especialidad, Grupo

# widgets compartidos: is_active y codigo no necesitan el ancho completo de su columna.
# is_active parte de BooleanWidget (no forms.Select) para conservar sus choices
# Desconocido/Sí/No; codigo parte de forms.TextInput, que ya es el widget por defecto
# de CharFilter, así que aquí solo se le añade el estilo.
WIDGET_ESTADO = BooleanWidget(attrs={'style': 'max-width: 140px'})
WIDGET_CODIGO = forms.TextInput(attrs={'style': 'max-width: 140px'})


class FilterSetConPlaceholder(django_filters.FilterSet):
    """usa el label de cada campo como placeholder (y lo oculta) para que el formulario
    de filtros (templates/crud/list.html) quepa en una sola fila sin labels encima de
    cada input. los <select> ignoran `placeholder`, así que ahí reutilizamos la opción
    vacía como sustituto visual del label.

    Cambiar:
        class GrupoFilter(django_filters.FilterSet):
    Por:
        class GrupoFilter(FilterSetConPlaceholder):
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.form.fields.values():
            etiqueta = campo.label
            if not etiqueta:
                continue
            if isinstance(campo.widget, forms.Select):
                if hasattr(campo, 'empty_label') and campo.empty_label is not None:
                    campo.empty_label = etiqueta
                elif campo.widget.choices and campo.widget.choices[0][0] == '':
                    campo.widget.choices[0] = ('', etiqueta)
            else:
                campo.widget.attrs.setdefault('placeholder', etiqueta)
            campo.label = ''


class GrupoFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(lookup_expr='icontains')
    codigo = django_filters.CharFilter(lookup_expr='icontains') #, widget=WIDGET_CODIGO)
    is_active = django_filters.BooleanFilter(widget=WIDGET_ESTADO)

    class Meta:
        model = Grupo
        fields = ['nombre', 'codigo', 'is_active']


class ClinicaFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(lookup_expr='icontains')
    ciudad = django_filters.CharFilter(lookup_expr='icontains')
    # codigo = django_filters.CharFilter(lookup_expr='icontains')
    is_active = django_filters.BooleanFilter(widget=WIDGET_ESTADO)

    class Meta:
        model = Clinica
        # fields = ['grupo', 'nombre', 'codigo', 'ciudad', 'is_active']
        fields = ['grupo', 'nombre', 'ciudad', 'is_active']


class EspecialidadFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(lookup_expr='icontains')
    profesion = django_filters.CharFilter(lookup_expr='icontains')
    is_active = django_filters.BooleanFilter(widget=WIDGET_ESTADO)

    class Meta:
        model = Especialidad
        fields = ['nombre', 'profesion', 'is_active']
