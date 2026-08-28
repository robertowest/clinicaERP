"""modelos de la app medicos: Medico y MedicoClinicaEspecialidad."""
from django.db import models

from apps.core.models import BaseModel, GroupOwnedModel


class Medico(GroupOwnedModel):
    """médico perteneciente a un grupo, ligado 1:1 a un `CustomUser`. soft delete vía
    `is_active` (heredado).

    `nombre`, `apellido` y `email` no se duplican aquí: se leen de `usuario` (ver
    `nombre_completo`/`email`, arquitectura.md §4). solo se guardan los datos que no
    existen en `CustomUser`: `colegiado` y `telefono` profesional.
    """

    usuario = models.OneToOneField(
        'usuarios.CustomUser', verbose_name='usuario', on_delete=models.PROTECT,
        related_name='medico',
    )
    colegiado = models.CharField('n.º de colegiado', max_length=12)
    telefono = models.CharField('teléfono', max_length=20, blank=True)

    class Meta:
        db_table = 'medi_medicos'
        verbose_name = 'médico'
        verbose_name_plural = 'médicos'
        ordering = ['grupo', 'usuario__last_name', 'usuario__first_name']
        constraints = [
            models.UniqueConstraint(
                fields=['grupo', 'colegiado'], name='medi_medico_unique_grupo_colegiado',
            ),
        ]

    @property
    def nombre_completo(self):
        return self.usuario.get_full_name() or self.usuario.username

    @property
    def email(self):
        return self.usuario.email

    def __str__(self):
        return f'{self.nombre_completo} ({self.colegiado})'


class MedicoClinicaEspecialidad(BaseModel):
    """especialidad que ejerce un médico en una clínica concreta: un médico puede tener una
    especialidad distinta en cada clínica donde trabaja (arquitectura.md §4).

    se mantiene deliberadamente desacoplada del catálogo `Clinica.especialidades` (lo que
    ofrece la clínica): no se valida que la especialidad asignada esté en ese catálogo, para
    que un cambio en el catálogo de la clínica no borre en cascada asignaciones de médicos
    (arquitectura.md §6, punto 5).
    """

    medico = models.ForeignKey(
        Medico, verbose_name='médico', on_delete=models.CASCADE,
        related_name='asignaciones_clinica',
    )
    clinica = models.ForeignKey(
        'organizacion.Clinica', verbose_name='clínica', on_delete=models.PROTECT,
        related_name='medicos_asignados',
    )
    especialidad = models.ForeignKey(
        'organizacion.Especialidad', verbose_name='especialidad', on_delete=models.PROTECT,
        related_name='asignaciones_medico',
    )

    class Meta:
        db_table = 'medi_medico_clinica_especialidades'
        verbose_name = 'especialidad de médico por clínica'
        verbose_name_plural = 'especialidades de médico por clínica'
        ordering = ['medico', 'clinica']
        constraints = [
            models.UniqueConstraint(
                fields=['medico', 'clinica'],
                name='medi_medicoclinicaespecialidad_unique_medico_clinica',
            ),
        ]

    def __str__(self):
        return f'{self.medico} · {self.especialidad} ({self.clinica})'
