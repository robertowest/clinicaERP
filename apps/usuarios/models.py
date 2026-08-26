"""modelos de la app usuarios: `CustomUser` y la tabla intermedia `UsuarioClinica`
que resuelve el rol de cada usuario en cada clínica (ver arquitectura.md §4).
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import BaseModel
from apps.usuarios.roles import Roles


class CustomUser(AbstractUser):
    """usuario personalizado del sistema; sustituye al `User` estándar de django.

    `grupo` es nullable: solo queda vacío para el `SUPERADMIN` de plataforma, que opera
    sobre varios grupos a la vez desde el django admin.
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


class UsuarioClinica(BaseModel):
    """rol de un usuario en una clínica concreta.

    el rol se guarda en esta relación, no como campo único en `CustomUser`, porque
    `CLINIC_ADMIN`/`DOCTOR`/`RECEPTIONIST` son roles ligados a una clínica (un usuario
    puede ser `CLINIC_ADMIN` en una clínica y `DOCTOR` en otra). `SUPERADMIN` y
    `GROUP_ADMIN` son roles de alcance grupo/plataforma: para esos dos, `clinica` queda
    en `None` (ver `Roles.ROLES_SIN_CLINICA`) en vez de tener un sistema de roles paralelo.

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
    rol = models.CharField('rol', max_length=20, choices=Roles.choices)

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
        return f'{self.usuario} · {self.get_rol_display()} ({destino})'
