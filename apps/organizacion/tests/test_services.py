"""tests de apps/organizacion/services.py."""
from django.test import TestCase

from apps.organizacion import services
from apps.organizacion.exceptions import CodigoDuplicadoError
from apps.organizacion.models import Especialidad, Grupo


class ServicesGrupoTests(TestCase):
    def test_crear_grupo_duplicado_lanza_codigo_duplicado_error(self):
        services.crear_grupo(nombre='Grupo Atenea', codigo='ATN')
        with self.assertRaises(CodigoDuplicadoError):
            services.crear_grupo(nombre='Otro grupo', codigo='ATN')


class ServicesClinicaTests(TestCase):
    def setUp(self):
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')

    def test_crear_clinica_duplicada_en_mismo_grupo_lanza_error(self):
        services.crear_clinica(grupo=self.grupo_a, nombre='Clínica Aldaia', codigo='ALD')
        with self.assertRaises(CodigoDuplicadoError):
            services.crear_clinica(grupo=self.grupo_a, nombre='Otra clínica', codigo='ALD')

    def test_crear_clinica_mismo_codigo_en_otro_grupo_no_falla(self):
        services.crear_clinica(grupo=self.grupo_a, nombre='Clínica Aldaia', codigo='ALD')
        clinica = services.crear_clinica(grupo=self.grupo_b, nombre='Clínica Aldaia', codigo='ALD')
        self.assertEqual(clinica.codigo, 'ALD')

    def test_asignar_y_quitar_especialidad_de_clinica(self):
        clinica = services.crear_clinica(grupo=self.grupo_a, nombre='Clínica Aldaia', codigo='ALD')
        cardiologia = Especialidad.objects.create(nombre='Cardiología')

        services.asignar_especialidad_a_clinica(clinica, cardiologia)
        self.assertIn(cardiologia, clinica.especialidades.all())

        services.quitar_especialidad_de_clinica(clinica, cardiologia)
        self.assertNotIn(cardiologia, clinica.especialidades.all())
