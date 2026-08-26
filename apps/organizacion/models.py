"""modelos de la app organizacion: Grupo, Clinica, Especialidad."""
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel, GroupOwnedModel


class Grupo(BaseModel):
    """grupo empresarial o médico; raíz del aislamiento multi-tenant."""

    nombre = models.CharField('nombre', max_length=50)
    codigo = models.CharField('código', max_length=16, unique=True)

    class Meta:
        db_table = 'orga_grupos'
        verbose_name = 'grupo'
        verbose_name_plural = 'grupos'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.codigo})'


class Especialidad(BaseModel):
    """catálogo global de especialidades médicas, compartido entre grupos."""

    nombre = models.CharField(
        _('Especialidad'), max_length=60, unique=True, null=False,
        help_text=_('Nombre de la disciplina, por ejemplo: Cardiología, Pediatría, Radiología, etc.')
    )
    profesion = models.CharField(
        _('Profesión'), max_length=60, unique=True, null=False,
        help_text=_('Nombre de la profesión, por ejemplo: Cardiólogo, Pediatra, Radiólogo, etc.')
    )
    imagen= models.ImageField(_('Imagen'), upload_to='especialidades/', null=True, blank=True)

    class Meta:
        db_table = 'orga_especialidades'
        verbose_name = 'especialidad'
        verbose_name_plural = 'especialidades'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Clinica(GroupOwnedModel):
    """clínica perteneciente a un grupo; soft delete vía `is_active` (heredado)."""

    nombre = models.CharField('nombre', max_length=100)
    codigo = models.CharField('código', max_length=16)
    domicilio = models.CharField('domicilio', max_length=255, blank=True)
    ciudad = models.CharField('ciudad', max_length=100, blank=True)
    codigo_postal = models.CharField('código postal', max_length=10, blank=True)
    telefono = models.CharField('teléfono', max_length=20, blank=True)
    email = models.EmailField('correo electrónico', blank=True)
    especialidades = models.ManyToManyField(
        Especialidad, verbose_name='especialidades', related_name='clinicas', blank=True,
    )

    class Meta:
        db_table = 'orga_clinicas'
        verbose_name = 'clínica'
        verbose_name_plural = 'clínicas'
        ordering = ['grupo', 'nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['grupo', 'codigo'], name='orga_clinica_unique_grupo_codigo',
            ),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.grupo.codigo})'
