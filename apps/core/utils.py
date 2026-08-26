import django_tables2 as tables
from django.utils.safestring import mark_safe

class BooleandColumn(tables.Column):
    """pinta los campos booleand como badge en vez de True/False."""

    def render(self, value):
        clase = 'text-bg-success' if value else 'text-bg-secondary'
        etiqueta = 'activo' if value else 'inactivo'
        return mark_safe(f'<span class="badge {clase}">{etiqueta}</span>')
