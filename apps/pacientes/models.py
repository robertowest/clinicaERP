"""modelos de la app pacientes: Paciente."""
from django.db import models

from apps.core.models import GroupOwnedModel


class Paciente(GroupOwnedModel):
    """
    paciente perteneciente a un grupo (no a una clínica concreta): puede ser atendido en
    cualquier clínica del grupo sin duplicar su ficha. soft delete vía `is_active` (heredado).
    """

    class DocumentoTipo(models.TextChoices):
        DNI = 'dni', 'DNI'
        NIE = 'nie', 'NIE'
        PASAPORTE = 'pass', 'Pasaporte'
        OTRO = 'otro', 'Otro'

    class Sexo(models.TextChoices):
        MASCULINO = 'M', 'Masculino'
        FEMENINO = 'F', 'Femenino'
        DESCONOCIDO = 'X', 'Desconocido'

    nhc = models.CharField('NHC', max_length=20, help_text='número de historia clínica')
    nombre = models.CharField('nombre', max_length=50)
    apellido = models.CharField('apellido', max_length=50)
    documento_tipo = models.CharField(
        'Documento tipo', max_length=4, choices=DocumentoTipo.choices,
    )
    documento_numero = models.CharField('Documento número', max_length=12)
    fecha_nacimiento = models.DateField('fecha de nacimiento')
    sexo = models.CharField('sexo', max_length=1, choices=Sexo.choices)
    email = models.EmailField('correo electrónico', blank=True)
    telefono = models.CharField('teléfono', max_length=12, blank=True)
    domicilio = models.CharField('domicilio', max_length=255, blank=True)
    ciudad = models.CharField('ciudad', max_length=100, blank=True)
    codigo_postal = models.CharField('código postal', max_length=10, blank=True)

    class Meta:
        db_table = 'paci_pacientes'
        verbose_name = 'paciente'
        verbose_name_plural = 'pacientes'
        ordering = ['grupo', 'apellido', 'nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['grupo', 'nhc'], name='paci_paciente_unique_grupo_nhc',
            ),
            models.UniqueConstraint(
                fields=['grupo', 'documento_tipo', 'documento_numero'],
                name='paci_paciente_unique_grupo_documento',
            ),
        ]

    def __str__(self):
        return f'{self.apellido}, {self.nombre} ({self.nhc})'
