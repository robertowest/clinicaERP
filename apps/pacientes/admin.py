from django.contrib import admin

from apps.pacientes.models import Paciente


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    """administración de pacientes por grupo."""

    list_display = ['nhc', 'nombre', 'apellido', 'documento_numero', 'grupo', 'is_active']
    search_fields = ['nhc', 'nombre', 'apellido', 'documento_numero']
    list_filter = ['is_active', 'grupo']
    autocomplete_fields = ['grupo']
    ordering = ['grupo', 'apellido', 'nombre']
