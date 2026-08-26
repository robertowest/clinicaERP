import django_tables2 as tables
from django.utils.safestring import mark_safe


class ActiveColumn(tables.Column):
    """pinta los campos booleand como badge en vez de True/False."""

    def render(self, value):
        clase = 'text-bg-success' if value else 'text-bg-secondary'
        etiqueta = 'Activo' if value else 'Inactivo'
        return mark_safe(f'<span class="badge {clase}">{etiqueta}</span>')


class BooleandColumn(tables.Column):
    """pinta los campos booleand como badge en vez de True/False."""

    def render(self, value):
        clase = 'text-bg-success' if value else 'text-bg-secondary'
        etiqueta = 'Sí' if value else 'No'
        return mark_safe(f'<span class="badge {clase}">{etiqueta}</span>')
