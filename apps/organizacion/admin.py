from django.contrib import admin

from apps.organizacion.models import Clinica, Especialidad, Grupo


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    """administración de grupos; excepción permitida a queries directas (ver arquitectura.md §5)."""

    list_display = ['nombre', 'codigo', 'is_active', 'created_at']
    search_fields = ['nombre', 'codigo']
    list_filter = ['is_active']
    ordering = ['nombre']


@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    """administración del catálogo global de especialidades."""

    list_display = ['nombre', 'profesion', 'imagen', 'is_active']
    search_fields = ['nombre', 'profesion']
    list_filter = ['is_active']
    ordering = ['nombre']


@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    """administración de clínicas por grupo."""

    list_display = ['nombre', 'codigo', 'grupo', 'ciudad', 'is_active']
    search_fields = ['nombre', 'codigo', 'ciudad']
    list_filter = ['is_active', 'grupo']
    autocomplete_fields = ['grupo', 'especialidades']
    ordering = ['grupo', 'nombre']
