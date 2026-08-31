"""
catálogo semilla de roles y permisos granulares de la plataforma.

los roles ya no son un `TextChoices` hardcodeado en un `CharField`: `UsuarioClinica.rol`
es un fk a `Rol` (proxy de `django.contrib.auth.models.Group`, ver `models.py`), y sus
permisos viven en `auth_group_permissions`/`auth_permission` — gestionables desde el
django admin sin tocar código ni redesplegar.

lo que queda aquí es solo la semilla inicial: `services.crear_catalogo_roles()` (llamada
desde la migración de datos que introdujo este esquema, desde la señal `post_migrate` de
`apps.py` y desde `seed.py`) la usa para crear/actualizar en bd los roles iniciales y sus
permisos — es idempotente, así que ampliar este catálogo más adelante no requiere una
migración nueva, solo volver a migrar/arrancar la app.

toda comprobación de autorización (vistas html, api, futuras apps) sigue pasando por
`services.usuario_tiene_permiso()`/`usuario_tiene_permiso_generico()`, nunca comparando
rol/string sueltos por su cuenta (punto único de autorización, arquitectura.md §6).
"""


class Roles:
    """
    códigos estables de los roles iniciales del sistema (`RolPerfil.codigo`).

    el antiguo `SUPERADMIN` se retira como rol asignable: ya lo cubre `CustomUser.is_superuser`,
    que `usuario_tiene_permiso()`/`usuario_tiene_permiso_generico()` comprueban antes que
    cualquier rol (y que django ya trata de forma nativa como acceso a todo permiso).
    """

    GROUP_ADMIN = 'GROUP_ADMIN'
    CLINIC_ADMIN = 'CLINIC_ADMIN'
    DOCTOR = 'DOCTOR'
    RECEPTIONIST = 'RECEPTIONIST'


# nombre visible (Group.name) y si el rol requiere clínica (RolPerfil.requiere_clinica),
# por código. las claves son las mismas que apps.usuarios.roles.Roles.
ROLES_INICIALES = {
    Roles.GROUP_ADMIN: {'nombre': 'Administrador de grupo', 'requiere_clinica': False},
    Roles.CLINIC_ADMIN: {'nombre': 'Administrador de clínica', 'requiere_clinica': True},
    Roles.DOCTOR: {'nombre': 'Médico', 'requiere_clinica': True},
    Roles.RECEPTIONIST: {'nombre': 'Recepción', 'requiere_clinica': True},
}

# catálogo de permisos granulares del dominio (prompt.md §7) y qué rol (por código) los
# concede; se amplía a medida que se incorporan módulos futuros (citas, facturación,
# historia...) sin tocar nunca las vistas/permission classes que consultan
# `usuario_tiene_permiso()`/`usuario_tiene_permiso_generico()`.
PERMISOS_POR_ROL = {
    Roles.GROUP_ADMIN: {
        'users.manage',
        'groups.view', 'groups.manage',
        'clinics.view', 'clinics.manage',
        'specialties.view', 'specialties.manage',
        'patients.view', 'patients.create', 'patients.update', 'patients.delete',
        'doctors.view', 'doctors.create', 'doctors.update', 'doctors.delete',
        'appointments.view', 'appointments.create',
        'billing.view', 'billing.manage',
    },
    Roles.CLINIC_ADMIN: {
        'clinics.view', 'clinics.manage',
        'specialties.view', 'specialties.manage',
        'patients.view', 'patients.create', 'patients.update',
        'doctors.view', 'doctors.create', 'doctors.update',
        'appointments.view', 'appointments.create',
        'billing.view',
    },
    Roles.DOCTOR: {
        'patients.view', 'patients.update',
        'doctors.view',
        'appointments.view', 'appointments.create',
    },
    Roles.RECEPTIONIST: {
        'patients.view', 'patients.create',
        'doctors.view',
        'appointments.view', 'appointments.create',
    },
}

# catálogo plano de codenames de `Permission` a crear en `PermisoPersonalizado` (unión de todos los permisos concedidos arriba).
CATALOGO_PERMISOS = {permiso for permisos in PERMISOS_POR_ROL.values() for permiso in permisos}
