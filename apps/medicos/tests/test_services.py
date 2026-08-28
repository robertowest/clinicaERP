"""tests de apps/medicos/services.py."""
from django.http import Http404
from django.test import TestCase

from apps.medicos import services
from apps.medicos.exceptions import (
    AsignacionDuplicadaError,
    ClinicaFueraDeGrupoError,
    ColegiadoDuplicadoError,
    UsuarioFueraDeGrupoError,
    UsuarioYaEsMedicoError,
)
from apps.organizacion.models import Clinica, Especialidad, Grupo
from apps.usuarios import services as usuarios_services
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles


class ServicesMedicoTests(TestCase):
    def setUp(self):
        self.grupo = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')
        self.usuario = CustomUser.objects.create_user(
            username='juan', password='clave123', grupo=self.grupo,
        )
        self.otro_usuario = CustomUser.objects.create_user(
            username='ana', password='clave123', grupo=self.grupo,
        )

    def test_crear_medico_colegiado_duplicado_lanza_error(self):
        services.crear_medico(grupo=self.grupo, usuario=self.usuario, colegiado='COL001')
        with self.assertRaises(ColegiadoDuplicadoError):
            services.crear_medico(grupo=self.grupo, usuario=self.otro_usuario, colegiado='COL001')

    def test_crear_medico_usuario_ya_es_medico_lanza_error(self):
        services.crear_medico(grupo=self.grupo, usuario=self.usuario, colegiado='COL001')
        with self.assertRaises(UsuarioYaEsMedicoError):
            services.crear_medico(grupo=self.grupo, usuario=self.usuario, colegiado='COL002')

    def test_crear_medico_usuario_fuera_de_grupo_lanza_error(self):
        otro_grupo = Grupo.objects.create(nombre='Grupo B', codigo='GRB')
        with self.assertRaises(UsuarioFueraDeGrupoError):
            services.crear_medico(grupo=otro_grupo, usuario=self.usuario, colegiado='COL001')

    def test_actualizar_medico_colegiado_duplicado_lanza_error(self):
        services.crear_medico(grupo=self.grupo, usuario=self.usuario, colegiado='COL001')
        otro = services.crear_medico(grupo=self.grupo, usuario=self.otro_usuario, colegiado='COL002')
        with self.assertRaises(ColegiadoDuplicadoError):
            services.actualizar_medico(otro, colegiado='COL001')

    def test_actualizar_medico_no_reasigna_usuario(self):
        medico = services.crear_medico(grupo=self.grupo, usuario=self.usuario, colegiado='COL001')
        services.actualizar_medico(medico, usuario=self.otro_usuario, telefono='600111222')
        medico.refresh_from_db()
        self.assertEqual(medico.usuario, self.usuario)
        self.assertEqual(medico.telefono, '600111222')

    def test_listar_usuarios_disponibles_excluye_a_quien_ya_es_medico(self):
        services.crear_medico(grupo=self.grupo, usuario=self.usuario, colegiado='COL001')
        disponibles = services.listar_usuarios_disponibles(grupo=self.grupo)
        self.assertNotIn(self.usuario, disponibles)
        self.assertIn(self.otro_usuario, disponibles)


class AsignacionClinicaEspecialidadTests(TestCase):
    def setUp(self):
        self.grupo = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')
        self.otro_grupo = Grupo.objects.create(nombre='Grupo B', codigo='GRB')
        self.usuario = CustomUser.objects.create_user(
            username='juan', password='clave123', grupo=self.grupo,
        )
        self.medico = services.crear_medico(grupo=self.grupo, usuario=self.usuario, colegiado='COL001')
        self.clinica = Clinica.objects.create(grupo=self.grupo, nombre='Aldaia', codigo='ALD')
        self.clinica_otro_grupo = Clinica.objects.create(
            grupo=self.otro_grupo, nombre='Torrent', codigo='TOR',
        )
        self.especialidad = Especialidad.objects.create(nombre='Cardiología', profesion='Cardiólogo')

    def test_asignar_clinica_fuera_de_grupo_lanza_error(self):
        with self.assertRaises(ClinicaFueraDeGrupoError):
            services.asignar_clinica_especialidad(
                medico=self.medico, clinica=self.clinica_otro_grupo, especialidad=self.especialidad,
            )

    def test_asignar_misma_clinica_dos_veces_lanza_error(self):
        services.asignar_clinica_especialidad(
            medico=self.medico, clinica=self.clinica, especialidad=self.especialidad,
        )
        with self.assertRaises(AsignacionDuplicadaError):
            services.asignar_clinica_especialidad(
                medico=self.medico, clinica=self.clinica, especialidad=self.especialidad,
            )

    def test_quitar_asignacion(self):
        asignacion = services.asignar_clinica_especialidad(
            medico=self.medico, clinica=self.clinica, especialidad=self.especialidad,
        )
        services.quitar_asignacion_clinica(asignacion)
        self.assertEqual(services.listar_asignaciones_clinica(medico=self.medico).count(), 0)


class VisibilidadPorRolTests(TestCase):
    """aislamiento multi-tenant crítico (ver claude.md/prompt.md §26): un usuario del grupo A
    no debe ver ni resolver por id directo un médico del grupo B."""

    def setUp(self):
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')
        self.usuario_medico_a = CustomUser.objects.create_user(
            username='medico_a', password='clave123', grupo=self.grupo_a,
        )
        self.usuario_medico_b = CustomUser.objects.create_user(
            username='medico_b', password='clave123', grupo=self.grupo_b,
        )
        self.medico_a = services.crear_medico(
            grupo=self.grupo_a, usuario=self.usuario_medico_a, colegiado='COL001',
        )
        self.medico_b = services.crear_medico(
            grupo=self.grupo_b, usuario=self.usuario_medico_b, colegiado='COL001',
        )
        self.superadmin = CustomUser.objects.create_user(
            username='root', password='clave123', is_superuser=True,
        )
        self.clinica_a = Clinica.objects.create(grupo=self.grupo_a, nombre='Aldaia', codigo='ALD')
        self.recepcion_a = CustomUser.objects.create_user(
            username='rec_a', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(
            usuario=self.recepcion_a, rol=Roles.RECEPTIONIST, clinica=self.clinica_a,
        )

    def test_superadmin_ve_todos_los_medicos(self):
        self.assertCountEqual(
            services.listar_medicos_visibles_para(self.superadmin),
            [self.medico_a, self.medico_b],
        )

    def test_usuario_de_un_grupo_solo_ve_los_medicos_de_su_grupo(self):
        self.assertCountEqual(
            services.listar_medicos_visibles_para(self.recepcion_a), [self.medico_a],
        )

    def test_no_resuelve_por_id_directo_un_medico_de_otro_grupo(self):
        with self.assertRaises(Http404):
            services.obtener_medico_visible_para(self.medico_b.pk, self.recepcion_a)
        self.assertEqual(
            services.obtener_medico_visible_para(self.medico_a.pk, self.recepcion_a),
            self.medico_a,
        )
