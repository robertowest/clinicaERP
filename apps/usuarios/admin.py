from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.usuarios.models import CustomUser, UsuarioClinica


class UsuarioClinicaInline(admin.TabularInline):
    """asignaciones de rol por clínica, editables desde la ficha del usuario."""

    model = UsuarioClinica
    extra = 1
    autocomplete_fields = ['clinica']


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """administración de usuarios; excepción permitida a queries directas (ver arquitectura §5)."""

    fieldsets = UserAdmin.fieldsets + (
        ('Organización', {'fields': ('grupo',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Organización', {'fields': ('grupo',)}),
    )
    list_display = ['username', 'email', 'grupo', 'is_staff', 'is_active']
    list_filter = UserAdmin.list_filter + ('grupo',)
    search_fields = ['username', 'first_name', 'last_name', 'email']
    autocomplete_fields = ['grupo']
    inlines = [UsuarioClinicaInline]


@admin.register(UsuarioClinica)
class UsuarioClinicaAdmin(admin.ModelAdmin):
    """administración directa de asignaciones, útil para auditar rol por clínica."""

    list_display = ['usuario', 'clinica', 'rol', 'is_active']
    list_filter = ['rol', 'is_active', 'clinica__grupo']
    search_fields = ['usuario__username', 'clinica__nombre']
    autocomplete_fields = ['usuario', 'clinica']
