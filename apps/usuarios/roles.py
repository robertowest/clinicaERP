"""roles y permisos centralizados de la plataforma.

toda comprobación de autorización (vistas html, api, futuras apps) importa `Roles`
y llama a `rol_tiene_permiso()` / `services.usuario_tiene_permiso()` desde aquí, nunca
compara strings de rol sueltos por el código.
"""
from django.db import models


class Roles(models.TextChoices):
    """roles iniciales del sistema (ver arquitectura.md §4 y prompt.md §7)."""

    SUPERADMIN = 'SUPERADMIN', 'Superadministrador'
    GROUP_ADMIN = 'GROUP_ADMIN', 'Administrador de grupo'
    CLINIC_ADMIN = 'CLINIC_ADMIN', 'Administrador de clínica'
    DOCTOR = 'DOCTOR', 'Médico'
    RECEPTIONIST = 'RECEPTIONIST', 'Recepción'


# roles de alcance grupo/plataforma: no están ligados a una clínica concreta, por eso
# `UsuarioClinica.clinica` es nullable solo para estos dos roles (ver arquitectura.md §4).
ROLES_SIN_CLINICA = {Roles.SUPERADMIN, Roles.GROUP_ADMIN}

# catálogo de permisos granulares por rol (prompt.md §7). se amplía a medida que se
# incorporan módulos futuros (citas, facturación, historia...) sin tocar nunca las
# vistas/permission classes que consultan `rol_tiene_permiso()`.
PERMISOS_POR_ROL = {
    Roles.SUPERADMIN: {'*'},
    Roles.GROUP_ADMIN: {
        'users.manage',
        'patients.view', 'patients.create', 'patients.update', 'patients.delete',
        'appointments.view', 'appointments.create',
        'billing.view', 'billing.manage',
    },
    Roles.CLINIC_ADMIN: {
        'patients.view', 'patients.create', 'patients.update',
        'appointments.view', 'appointments.create',
        'billing.view',
    },
    Roles.DOCTOR: {
        'patients.view', 'patients.update',
        'appointments.view', 'appointments.create',
    },
    Roles.RECEPTIONIST: {
        'patients.view', 'patients.create',
        'appointments.view', 'appointments.create',
    },
}


def rol_tiene_permiso(rol, permiso):
    """indica si `rol` concede acceso al permiso granular `permiso` (ej. "patients.view").

    `SUPERADMIN` tiene el comodín `*`: acceso a cualquier permiso presente o futuro.
    """
    permisos = PERMISOS_POR_ROL.get(rol, set())
    return '*' in permisos or permiso in permisos
