"""modelos de la app usuarios: `CustomUser`, el catálogo de roles (`Rol`/`RolPerfil`/
`PermisoPersonalizado`) y la tabla intermedia `UsuarioClinica` que resuelve el rol de
cada usuario en cada clínica (ver arquitectura.md §4).
"""
from django.contrib.auth.models import AbstractUser, Group
from django.db import models

from apps.core.models import BaseModel


class CustomUser(AbstractUser):
    """usuario personalizado del sistema; sustituye al `User` estándar de django.

    `grupo` es nullable: solo queda vacío para el superadministrador de plataforma
    (`is_superuser=True`), que opera sobre varios grupos a la vez desde el django admin.
    """

    grupo = models.ForeignKey(
        'organizacion.Grupo',
        verbose_name='grupo',
        on_delete=models.PROTECT,
        related_name='usuarios',
        null=True,
        blank=True,
    )

    class Meta:
        db_table = 'usua_usuarios'
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        ordering = ['username']

    def __str__(self):
        return self.get_full_name() or self.username


class Rol(Group):
    """un rol del sistema es un `django.contrib.auth.models.Group`: se reutiliza tal cual
    `auth_group`/`auth_group_permissions`/`auth_permission` (gestionables desde el django
    admin sin tocar código ni redesplegar) en vez de un catálogo de roles/permisos
    hardcodeado en python.

    es un proxy, no una tabla nueva: `Group` ya existe (lo usa `auth`, y `CustomUser` lo
    hereda de `AbstractUser` vía `groups`/`user_permissions`, sin relación con este `Rol`,
    que es de alcance por clínica — ver `UsuarioClinica`). se declara como proxy en vez de
    usar `Group` directamente para no confundirlo con `apps.organizacion.Grupo` (grupo
    empresarial/tenant): sin este proxy, el admin mostraría dos secciones "Grupos".
    """

    class Meta:
        proxy = True
        verbose_name = 'rol'
        verbose_name_plural = 'roles'

    def __str__(self):
        return self.name


class PermisoPersonalizado(models.Model):
    """modelo contenedor sin tabla propia (`managed=False`): existe únicamente para que
    los permisos granulares del dominio (`patients.view`, `billing.manage`...) cuelguen de
    un `ContentType` real, tal y como exige `django.contrib.auth.models.Permission`, sin
    atarlos 1:1 al ciclo crud de un modelo de negocio concreto (patrón estándar de django
    para "permisos sin modelo"). el catálogo real de permisos vive en
    `apps.usuarios.roles.CATALOGO_PERMISOS` y se materializa en bd vía
    `services.crear_catalogo_roles()`.
    """

    class Meta:
        managed = False
        default_permissions = ()
        verbose_name = 'permiso personalizado'
        verbose_name_plural = 'permisos personalizados'


class RolPerfil(models.Model):
    """metadatos de un `Rol` que `Group` no puede modelar (no es abstracto, no admite
    campos por herencia): un código estable para resolverlo sin depender de `Group.name`
    (texto libre, editable desde el admin) y si el rol necesita una clínica concreta.
    """

    rol = models.OneToOneField(
        Rol, verbose_name='rol', on_delete=models.CASCADE, related_name='perfil',
    )
    codigo = models.CharField(
        'código', max_length=20, unique=True,
        help_text='identificador estable del rol (ver apps.usuarios.roles.Roles); '
                   'no cambia aunque se renombre el rol desde el admin.',
    )
    requiere_clinica = models.BooleanField(
        'requiere clínica', default=True,
        help_text='si el rol es de alcance grupo/plataforma (ej. administrador de grupo), '
                   'desmarcar: sus asignaciones no llevan clínica concreta.',
    )

    class Meta:
        db_table = 'usua_rol_perfiles'
        verbose_name = 'perfil de rol'
        verbose_name_plural = 'perfiles de rol'
        ordering = ['codigo']

    def __str__(self):
        return self.codigo


class UsuarioClinica(BaseModel):
    """rol de un usuario en una clínica concreta.

    el rol se guarda en esta relación, no como campo único en `CustomUser`, porque
    `CLINIC_ADMIN`/`DOCTOR`/`RECEPTIONIST` son roles ligados a una clínica (un usuario
    puede ser `CLINIC_ADMIN` en una clínica y `DOCTOR` en otra). los roles de alcance
    grupo/plataforma (`RolPerfil.requiere_clinica=False`, ej. `GROUP_ADMIN`) dejan
    `clinica` en `None` en vez de tener un sistema de roles paralelo.

    la validación `clinica.grupo == usuario.grupo` se fuerza en `services.py`, no solo
    aquí ni en el serializer (arquitectura.md §4).
    """

    usuario = models.ForeignKey(
        CustomUser, verbose_name='usuario', on_delete=models.CASCADE,
        related_name='clinicas_asignadas',
    )
    clinica = models.ForeignKey(
        'organizacion.Clinica', verbose_name='clínica', on_delete=models.PROTECT,
        related_name='usuarios_asignados', null=True, blank=True,
    )
    rol = models.ForeignKey(
        Rol, verbose_name='rol', on_delete=models.PROTECT, related_name='asignaciones',
    )

    class Meta:
        db_table = 'usua_usuario_clinicas'
        verbose_name = 'asignación de usuario a clínica'
        verbose_name_plural = 'asignaciones de usuario a clínica'
        ordering = ['usuario', 'clinica']
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'clinica'], name='usua_usuarioclinica_unique_usuario_clinica',
            ),
        ]

    def __str__(self):
        destino = self.clinica.nombre if self.clinica else 'grupo'
        return f'{self.usuario} · {self.rol} ({destino})'
