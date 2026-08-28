from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group

from apps.usuarios.models import CustomUser, Rol, RolPerfil, UsuarioClinica

# `Rol` es un proxy de `Group` (ver models.py): desregistramos el `Group` "de serie" para
# no tener dos secciones "Grupos" en el admin (una sería en realidad el catálogo de roles).
admin.site.unregister(Group)


class RolPerfilInline(admin.StackedInline):
    """código estable y si el rol requiere clínica, editable desde la propia ficha del rol."""

    model = RolPerfil
    can_delete = False


@admin.register(Rol)
class RolAdmin(GroupAdmin):
    """reutiliza el admin estándar de `Group` (incluida la gestión de permisos m2m)
    sobre el proxy `Rol`."""

    inlines = [RolPerfilInline]
    search_fields = ['name']


class UsuarioClinicaInline(admin.TabularInline):
    """asignaciones de rol por clínica, editables desde la ficha del usuario."""

    model = UsuarioClinica
    extra = 1
    autocomplete_fields = ['clinica', 'rol']


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
    autocomplete_fields = ['usuario', 'clinica', 'rol']
