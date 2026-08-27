"""tests de apps/organizacion/services.py."""
from django.http import Http404
from django.test import TestCase

from apps.organizacion import services
from apps.organizacion.exceptions import CodigoDuplicadoError
from apps.organizacion.models import Especialidad, Grupo
from apps.usuarios import services as usuarios_services
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles


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


class VisibilidadPorRolTests(TestCase):
    """aislamiento multi-tenant crítico (ver claude.md): un rol de un grupo/clínica no debe
    ver ni resolver por id directo datos de otro grupo/clínica donde no tiene alcance.
    """

    def setUp(self):
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')
        self.clinica_a1 = services.crear_clinica(grupo=self.grupo_a, nombre='Aldaia', codigo='ALD')
        self.clinica_a2 = services.crear_clinica(grupo=self.grupo_a, nombre='Torrent', codigo='TOR')
        self.clinica_b1 = services.crear_clinica(grupo=self.grupo_b, nombre='Externa', codigo='EXT')
        self.superadmin = CustomUser.objects.create_user(
            username='root', password='clave123', is_superuser=True,
        )
        self.group_admin = CustomUser.objects.create_user(
            username='admin_a', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(usuario=self.group_admin, rol=Roles.GROUP_ADMIN)
        self.clinic_admin = CustomUser.objects.create_user(
            username='admin_ald', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(
            usuario=self.clinic_admin, rol=Roles.CLINIC_ADMIN, clinica=self.clinica_a1,
        )

    def test_superadmin_ve_todos_los_grupos_y_clinicas(self):
        self.assertCountEqual(
            services.listar_grupos_visibles_para(self.superadmin), [self.grupo_a, self.grupo_b],
        )
        self.assertCountEqual(
            services.listar_clinicas_visibles_para(self.superadmin),
            [self.clinica_a1, self.clinica_a2, self.clinica_b1],
        )

    def test_group_admin_solo_ve_su_grupo_y_las_clinicas_de_ese_grupo(self):
        self.assertCountEqual(
            services.listar_grupos_visibles_para(self.group_admin), [self.grupo_a],
        )
        self.assertCountEqual(
            services.listar_clinicas_visibles_para(self.group_admin),
            [self.clinica_a1, self.clinica_a2],
        )

    def test_clinic_admin_solo_ve_las_clinicas_donde_tiene_el_rol_asignado(self):
        self.assertCountEqual(
            services.listar_clinicas_visibles_para(self.clinic_admin), [self.clinica_a1],
        )

    def test_clinic_admin_no_resuelve_por_id_directo_una_clinica_fuera_de_su_alcance(self):
        with self.assertRaises(Http404):
            services.obtener_clinica_visible_para(self.clinica_a2.pk, self.clinic_admin)
        with self.assertRaises(Http404):
            services.obtener_clinica_visible_para(self.clinica_b1.pk, self.clinic_admin)
        # sí resuelve la suya:
        self.assertEqual(
            services.obtener_clinica_visible_para(self.clinica_a1.pk, self.clinic_admin),
            self.clinica_a1,
        )

    def test_group_admin_no_resuelve_por_id_directo_el_grupo_de_otro_grupo(self):
        with self.assertRaises(Http404):
            services.obtener_grupo_visible_para(self.grupo_b.pk, self.group_admin)
        self.assertEqual(
            services.obtener_grupo_visible_para(self.grupo_a.pk, self.group_admin), self.grupo_a,
        )

    def test_usuario_sin_rol_no_ve_ninguna_clinica(self):
        # `listar_clinicas_visibles_para` sí depende del rol (solo GROUP_ADMIN/CLINIC_ADMIN
        # tienen alcance); sin ningún rol asignado no ve ninguna clínica. `groups.view`/
        # `clinics.view` (permission class/mixin) son quienes impiden llegar aquí en la
        # práctica: `listar_grupos_visibles_para` por sí sola solo acota por `grupo_id` de
        # pertenencia, no por rol.
        sin_rol = CustomUser.objects.create_user(
            username='sin_rol', password='clave123', grupo=self.grupo_a,
        )
        self.assertCountEqual(services.listar_clinicas_visibles_para(sin_rol), [])
