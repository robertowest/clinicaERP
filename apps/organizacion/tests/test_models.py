"""tests de constraints y comportamiento de los modelos de organizacion."""
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.organizacion import services
from apps.organizacion.models import Clinica, Especialidad, Grupo


class GrupoModelTests(TestCase):
    def test_codigo_unico_lanza_integrity_error(self):
        Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Grupo.objects.create(nombre='Otro grupo', codigo='ATN')

    def test_str(self):
        grupo = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')
        self.assertEqual(str(grupo), 'Grupo Atenea (ATN)')


class EspecialidadModelTests(TestCase):
    def test_nombre_unico_lanza_integrity_error(self):
        Especialidad.objects.create(nombre='Cardiología')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Especialidad.objects.create(nombre='Cardiología')

    def test_str(self):
        especialidad = Especialidad.objects.create(nombre='Cardiología')
        self.assertEqual(str(especialidad), 'Cardiología')


class ClinicaModelTests(TestCase):
    def setUp(self):
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')

    def test_codigo_unico_por_grupo(self):
        Clinica.objects.create(grupo=self.grupo_a, nombre='Clínica Aldaia', codigo='ALD')
        # mismo código en otro grupo: permitido
        Clinica.objects.create(grupo=self.grupo_b, nombre='Clínica Aldaia', codigo='ALD')
        # mismo código en el mismo grupo: falla
        with self.assertRaises(IntegrityError), transaction.atomic():
            Clinica.objects.create(grupo=self.grupo_a, nombre='Otra clínica', codigo='ALD')

    def test_soft_delete_no_borra_fila(self):
        clinica = Clinica.objects.create(grupo=self.grupo_a, nombre='Clínica Aldaia', codigo='ALD')
        services.desactivar_clinica(clinica)
        clinica.refresh_from_db()
        self.assertFalse(clinica.is_active)
        self.assertTrue(Clinica.objects.filter(pk=clinica.pk).exists())

    def test_str(self):
        clinica = Clinica.objects.create(grupo=self.grupo_a, nombre='Clínica Aldaia', codigo='ALD')
        self.assertEqual(str(clinica), 'Clínica Aldaia (GRA)')
