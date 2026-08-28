"""tests de apps/pacientes/services.py."""
from django.http import Http404
from django.test import TestCase

from apps.organizacion.models import Clinica, Grupo
from apps.pacientes import services
from apps.pacientes.exceptions import DocumentoDuplicadoError, NhcDuplicadoError
from apps.pacientes.models import Paciente
from apps.usuarios import services as usuarios_services
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles


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


class ServicesPacienteTests(TestCase):
    def setUp(self):
        self.grupo = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')

    def test_crear_paciente_nhc_duplicado_lanza_error(self):
        services.crear_paciente(grupo=self.grupo, **_datos_paciente())
        with self.assertRaises(NhcDuplicadoError):
            services.crear_paciente(
                grupo=self.grupo, **_datos_paciente(documento_numero='87654321B'),
            )

    def test_crear_paciente_documento_duplicado_lanza_error(self):
        services.crear_paciente(grupo=self.grupo, **_datos_paciente())
        with self.assertRaises(DocumentoDuplicadoError):
            services.crear_paciente(grupo=self.grupo, **_datos_paciente(nhc='NHC002'))

    def test_actualizar_paciente_nhc_duplicado_lanza_error(self):
        services.crear_paciente(grupo=self.grupo, **_datos_paciente())
        otro = services.crear_paciente(
            grupo=self.grupo, **_datos_paciente(nhc='NHC002', documento_numero='87654321B'),
        )
        with self.assertRaises(NhcDuplicadoError):
            services.actualizar_paciente(otro, nhc='NHC001')

    def test_actualizar_paciente_documento_duplicado_lanza_error(self):
        services.crear_paciente(grupo=self.grupo, **_datos_paciente())
        otro = services.crear_paciente(
            grupo=self.grupo, **_datos_paciente(nhc='NHC002', documento_numero='87654321B'),
        )
        with self.assertRaises(DocumentoDuplicadoError):
            services.actualizar_paciente(
                otro, documento_tipo=Paciente.DocumentoTipo.DNI, documento_numero='12345678A',
            )

    def test_actualizar_paciente_sin_tocar_nhc_ni_documento_no_falla(self):
        paciente = services.crear_paciente(grupo=self.grupo, **_datos_paciente())
        actualizado = services.actualizar_paciente(paciente, telefono='600111222')
        self.assertEqual(actualizado.telefono, '600111222')


class VisibilidadPorRolTests(TestCase):
    """aislamiento multi-tenant crítico (ver claude.md/prompt.md §26): un usuario del grupo A
    no debe ver ni resolver por id directo un paciente del grupo B."""

    def setUp(self):
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')
        self.paciente_a = services.crear_paciente(grupo=self.grupo_a, **_datos_paciente())
        self.paciente_b = services.crear_paciente(
            grupo=self.grupo_b, **_datos_paciente(nhc='NHC002', documento_numero='87654321B'),
        )
        self.superadmin = CustomUser.objects.create_user(
            username='root', password='clave123', is_superuser=True,
        )
        self.clinica_a = Clinica.objects.create(grupo=self.grupo_a, nombre='Aldaia', codigo='ALD')
        self.doctor_a = CustomUser.objects.create_user(
            username='doc_a', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(
            usuario=self.doctor_a, rol=Roles.DOCTOR, clinica=self.clinica_a,
        )

    def test_superadmin_ve_todos_los_pacientes(self):
        self.assertCountEqual(
            services.listar_pacientes_visibles_para(self.superadmin),
            [self.paciente_a, self.paciente_b],
        )

    def test_usuario_de_un_grupo_solo_ve_los_pacientes_de_su_grupo(self):
        self.assertCountEqual(
            services.listar_pacientes_visibles_para(self.doctor_a), [self.paciente_a],
        )

    def test_no_resuelve_por_id_directo_un_paciente_de_otro_grupo(self):
        with self.assertRaises(Http404):
            services.obtener_paciente_visible_para(self.paciente_b.pk, self.doctor_a)
        self.assertEqual(
            services.obtener_paciente_visible_para(self.paciente_a.pk, self.doctor_a),
            self.paciente_a,
        )
