"""tests de apps.usuarios.services."""
from django.test import TestCase

from apps.organizacion.models import Clinica, Grupo
from apps.usuarios import services
from apps.usuarios.exceptions import (
    ClinicaFueraDeGrupoError,
    RolNoAceptaClinicaError,
    RolRequiereClinicaError,
    UsuarioDuplicadoError,
)
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles


class CrearUsuarioTests(TestCase):
    def test_crea_usuario_con_password_hasheada(self):
        usuario = services.crear_usuario(username='ana', password='clave-larga-123')
        self.assertNotEqual(usuario.password, 'clave-larga-123')
        self.assertTrue(usuario.check_password('clave-larga-123'))

    def test_username_duplicado_lanza_excepcion(self):
        services.crear_usuario(username='ana', password='clave-larga-123')
        with self.assertRaises(UsuarioDuplicadoError):
            services.crear_usuario(username='ana', password='otra-clave-456')


class AsignarRolTests(TestCase):
    def setUp(self):
        self.grupo_a = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')
        self.grupo_b = Grupo.objects.create(nombre='Otro grupo', codigo='OTR')
        self.clinica_a = Clinica.objects.create(grupo=self.grupo_a, nombre='Aldaia', codigo='ALD')
        self.clinica_b = Clinica.objects.create(grupo=self.grupo_b, nombre='Externa', codigo='EXT')
        self.usuario = CustomUser.objects.create_user(
            username='ana', password='clave123', grupo=self.grupo_a,
        )

    def test_rol_doctor_requiere_clinica(self):
        with self.assertRaises(RolRequiereClinicaError):
            services.asignar_rol(usuario=self.usuario, rol=Roles.DOCTOR, clinica=None)

    def test_rol_group_admin_no_admite_clinica(self):
        with self.assertRaises(RolNoAceptaClinicaError):
            services.asignar_rol(
                usuario=self.usuario, rol=Roles.GROUP_ADMIN, clinica=self.clinica_a,
            )

    def test_clinica_fuera_del_grupo_lanza_excepcion(self):
        with self.assertRaises(ClinicaFueraDeGrupoError):
            services.asignar_rol(usuario=self.usuario, rol=Roles.DOCTOR, clinica=self.clinica_b)

    def test_asignacion_valida_se_crea(self):
        asignacion = services.asignar_rol(
            usuario=self.usuario, rol=Roles.DOCTOR, clinica=self.clinica_a,
        )
        self.assertEqual(asignacion.usuario, self.usuario)
        self.assertEqual(asignacion.clinica, self.clinica_a)


class UsuarioTienePermisoTests(TestCase):
    def setUp(self):
        self.grupo = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')
        self.clinica = Clinica.objects.create(grupo=self.grupo, nombre='Aldaia', codigo='ALD')
        self.otra_clinica = Clinica.objects.create(grupo=self.grupo, nombre='Torrent', codigo='TOR')
        self.usuario = CustomUser.objects.create_user(
            username='ana', password='clave123', grupo=self.grupo,
        )

    def test_doctor_tiene_permiso_solo_en_su_clinica(self):
        tiene_permiso = services.usuario_tiene_permiso
        services.asignar_rol(usuario=self.usuario, rol=Roles.DOCTOR, clinica=self.clinica)
        self.assertTrue(tiene_permiso(self.usuario, self.clinica, 'patients.view'))
        self.assertFalse(tiene_permiso(self.usuario, self.otra_clinica, 'patients.view'))

    def test_doctor_no_tiene_permiso_de_facturacion(self):
        services.asignar_rol(usuario=self.usuario, rol=Roles.DOCTOR, clinica=self.clinica)
        tiene_permiso = services.usuario_tiene_permiso(self.usuario, self.clinica, 'billing.manage')
        self.assertFalse(tiene_permiso)

    def test_group_admin_tiene_permiso_en_cualquier_clinica_del_grupo(self):
        tiene_permiso = services.usuario_tiene_permiso
        services.asignar_rol(usuario=self.usuario, rol=Roles.GROUP_ADMIN)
        self.assertTrue(tiene_permiso(self.usuario, self.clinica, 'billing.manage'))
        self.assertTrue(tiene_permiso(self.usuario, self.otra_clinica, 'billing.manage'))

    def test_superusuario_tiene_cualquier_permiso(self):
        self.usuario.is_superuser = True
        self.usuario.save(update_fields=['is_superuser'])
        self.assertTrue(services.usuario_tiene_permiso(self.usuario, self.clinica, 'lo.que.sea'))


class ObtenerDatosMeTests(TestCase):
    def test_rol_de_grupo_expande_a_todas_las_clinicas_activas(self):
        grupo = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')
        Clinica.objects.create(grupo=grupo, nombre='Aldaia', codigo='ALD')
        Clinica.objects.create(grupo=grupo, nombre='Torrent', codigo='TOR')
        usuario = CustomUser.objects.create_user(username='ana', password='clave123', grupo=grupo)
        services.asignar_rol(usuario=usuario, rol=Roles.GROUP_ADMIN)

        datos = services.obtener_datos_me(usuario)

        self.assertEqual(datos['group']['codigo'], 'ATN')
        self.assertEqual(len(datos['clinics']), 2)
        self.assertEqual(datos['roles'], [Roles.GROUP_ADMIN])

    def test_usuario_sin_grupo_ni_asignaciones(self):
        usuario = CustomUser.objects.create_user(
            username='root', password='clave123', is_staff=True,
        )
        datos = services.obtener_datos_me(usuario)
        self.assertIsNone(datos['group'])
        self.assertEqual(datos['clinics'], [])
        self.assertEqual(datos['roles'], [])
