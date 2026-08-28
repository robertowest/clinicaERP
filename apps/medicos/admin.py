from django.contrib import admin

from apps.medicos.models import Medico, MedicoClinicaEspecialidad


class MedicoClinicaEspecialidadInline(admin.TabularInline):
    """especialidades del médico por clínica, editables desde la propia ficha del médico."""

    model = MedicoClinicaEspecialidad
    extra = 1
    autocomplete_fields = ['clinica', 'especialidad']


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    """administración de médicos por grupo."""

    list_display = ['colegiado', 'nombre_completo', 'grupo', 'is_active']
    search_fields = ['colegiado', 'usuario__first_name', 'usuario__last_name', 'usuario__username']
    list_filter = ['is_active', 'grupo']
    autocomplete_fields = ['grupo', 'usuario']
    ordering = ['grupo', 'usuario__last_name']
    inlines = [MedicoClinicaEspecialidadInline]


@admin.register(MedicoClinicaEspecialidad)
class MedicoClinicaEspecialidadAdmin(admin.ModelAdmin):
    """administración directa de asignaciones, útil para auditar especialidad por clínica."""

    list_display = ['medico', 'clinica', 'especialidad']
    list_filter = ['clinica__grupo', 'especialidad']
    search_fields = ['medico__colegiado', 'medico__usuario__first_name', 'medico__usuario__last_name']
    autocomplete_fields = ['medico', 'clinica', 'especialidad']
