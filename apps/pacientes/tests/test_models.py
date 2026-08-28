"""tests de constraints y comportamiento del modelo Paciente."""
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.organizacion.models import Grupo
from apps.pacientes import services
from apps.pacientes.models import Paciente


def _datos_paciente(**overrides):
    datos = {
        'nhc': 'NHC001',
        'nombre': 'Juan',
        'apellido': 'Pérez',
        'documento_tipo': Paciente.DocumentoTipo.DNI,
        'documento_numero': '12345678A',
        'fecha_nacimiento': '1980-01-01',
        'sexo': Paciente.Sexo.MASCULINO,
    }
    datos.update(overrides)
    return datos


class PacienteModelTests(TestCase):
    def setUp(self):
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')

    def test_nhc_unico_por_grupo(self):
        Paciente.objects.create(grupo=self.grupo_a, **_datos_paciente())
        # mismo nhc en otro grupo: permitido
        Paciente.objects.create(
            grupo=self.grupo_b, **_datos_paciente(documento_numero='87654321B'),
        )
        # mismo nhc en el mismo grupo: falla
        with self.assertRaises(IntegrityError), transaction.atomic():
            Paciente.objects.create(
                grupo=self.grupo_a, **_datos_paciente(documento_numero='11111111C'),
            )

    def test_documento_unico_por_grupo(self):
        Paciente.objects.create(grupo=self.grupo_a, **_datos_paciente())
        # mismo documento en otro grupo: permitido
        Paciente.objects.create(grupo=self.grupo_b, **_datos_paciente(nhc='NHC002'))
        # mismo documento en el mismo grupo: falla
        with self.assertRaises(IntegrityError), transaction.atomic():
            Paciente.objects.create(grupo=self.grupo_a, **_datos_paciente(nhc='NHC003'))

    def test_soft_delete_no_borra_fila(self):
        paciente = Paciente.objects.create(grupo=self.grupo_a, **_datos_paciente())
        services.desactivar_paciente(paciente)
        paciente.refresh_from_db()
        self.assertFalse(paciente.is_active)
        self.assertTrue(Paciente.objects.filter(pk=paciente.pk).exists())

    def test_str(self):
        paciente = Paciente.objects.create(grupo=self.grupo_a, **_datos_paciente())
        self.assertEqual(str(paciente), 'Pérez, Juan (NHC001)')
