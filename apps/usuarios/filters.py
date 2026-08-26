"""filtros django-filter de usuarios; declaran Meta.model por diseño de la librería
(excepción permitida a acceso directo al modelo, ver arquitectura.md §5)."""
import django_filters
from django_filters.widgets import BooleanWidget

from apps.usuarios.models import CustomUser

WIDGET_ESTADO = BooleanWidget(attrs={'style': 'max-width: 140px'})


class UsuarioFilter(django_filters.FilterSet):
    username = django_filters.CharFilter(lookup_expr='icontains', label='Usuario')
    email = django_filters.CharFilter(lookup_expr='icontains', label='eMail')
    is_active = django_filters.BooleanFilter(widget=WIDGET_ESTADO)
    is_staff = django_filters.BooleanFilter(widget=WIDGET_ESTADO)

    class Meta:
        model = CustomUser
        fields = ['grupo', 'username', 'email', 'is_active', 'is_staff']
