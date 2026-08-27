"""tests de la api de organizacion: control de acceso basado en roles/permisos granulares
(apps.usuarios.roles.PERMISOS_POR_ROL), no en is_staff.
"""
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.organizacion.models import Clinica, Especialidad, Grupo
from apps.usuarios import services as usuarios_services
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles


class GrupoApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')
        self.superadmin = CustomUser.objects.create_user(
            username='root', password='clave123', is_superuser=True,
        )
        self.group_admin_a = CustomUser.objects.create_user(
            username='admin_a', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(usuario=self.group_admin_a, rol=Roles.GROUP_ADMIN)
        self.sin_rol = CustomUser.objects.create_user(
            username='ana', password='clave123', grupo=self.grupo_a,
        )

    def test_requiere_autenticacion(self):
        respuesta = self.client.get('/api/v1/grupos/')
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sin_permiso_no_puede_acceder(self):
        self.client.force_authenticate(self.sin_rol)
        respuesta = self.client.get('/api/v1/grupos/')
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_admin_solo_lista_su_propio_grupo(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.get('/api/v1/grupos/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['count'], 1)
        self.assertEqual(respuesta.data['results'][0]['codigo'], 'GRA')

    def test_group_admin_no_resuelve_por_id_directo_el_grupo_de_otro_grupo(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.get(f'/api/v1/grupos/{self.grupo_b.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_group_admin_edita_su_propio_grupo(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.patch(
            f'/api/v1/grupos/{self.grupo_a.pk}/', {'nombre': 'Renombrado'},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_group_admin_no_puede_crear_grupos_nuevos(self):
        # crear un grupo da de alta un tenant nuevo: sigue siendo exclusivo de superadmin.
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.post('/api/v1/grupos/', {'nombre': 'Grupo C', 'codigo': 'GRC'})
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_superadmin_ve_y_crea_cualquier_grupo(self):
        self.client.force_authenticate(self.superadmin)
        respuesta = self.client.get('/api/v1/grupos/')
        self.assertEqual(respuesta.data['count'], 2)

        respuesta = self.client.post('/api/v1/grupos/', {'nombre': 'Grupo C', 'codigo': 'GRC'})
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

    def test_crear_codigo_duplicado_devuelve_400(self):
        self.client.force_authenticate(self.superadmin)
        respuesta = self.client.post('/api/v1/grupos/', {'nombre': 'Otro', 'codigo': 'GRA'})
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)


class ClinicaApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')
        self.clinica_a1 = Clinica.objects.create(grupo=self.grupo_a, nombre='Aldaia', codigo='ALD')
        self.clinica_a2 = Clinica.objects.create(grupo=self.grupo_a, nombre='Torrent', codigo='TOR')
        self.clinica_b1 = Clinica.objects.create(grupo=self.grupo_b, nombre='Externa', codigo='EXT')
        self.cardiologia = Especialidad.objects.create(nombre='Cardiología')
        self.superadmin = CustomUser.objects.create_user(
            username='root', password='clave123', is_superuser=True,
        )
        self.group_admin_a = CustomUser.objects.create_user(
            username='admin_a', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(usuario=self.group_admin_a, rol=Roles.GROUP_ADMIN)
        self.clinic_admin_a1 = CustomUser.objects.create_user(
            username='admin_ald', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(
            usuario=self.clinic_admin_a1, rol=Roles.CLINIC_ADMIN, clinica=self.clinica_a1,
        )
        self.doctor_a1 = CustomUser.objects.create_user(
            username='doc_ald', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(
            usuario=self.doctor_a1, rol=Roles.DOCTOR, clinica=self.clinica_a1,
        )

    def test_requiere_autenticacion(self):
        respuesta = self.client.get('/api/v1/clinicas/')
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_doctor_no_tiene_acceso_a_organizacion(self):
        self.client.force_authenticate(self.doctor_a1)
        respuesta = self.client.get('/api/v1/clinicas/')
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_admin_lista_las_clinicas_de_su_grupo_no_las_de_otro(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.get('/api/v1/clinicas/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        codigos = {c['codigo'] for c in respuesta.data['results']}
        self.assertEqual(codigos, {'ALD', 'TOR'})

    def test_clinic_admin_lista_solo_la_clinica_donde_tiene_el_rol(self):
        self.client.force_authenticate(self.clinic_admin_a1)
        respuesta = self.client.get('/api/v1/clinicas/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        codigos = {c['codigo'] for c in respuesta.data['results']}
        self.assertEqual(codigos, {'ALD'})

    def test_clinic_admin_no_resuelve_por_id_directo_una_clinica_ajena(self):
        self.client.force_authenticate(self.clinic_admin_a1)
        respuesta = self.client.get(f'/api/v1/clinicas/{self.clinica_a2.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)
        respuesta = self.client.get(f'/api/v1/clinicas/{self.clinica_b1.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_group_admin_no_puede_crear_clinica_en_otro_grupo(self):
        # el queryset del campo `grupo` del serializer se acota al alcance del usuario:
        # enviar el id de un grupo ajeno debe fallar como valor inválido, no colarse.
        self.client.force_authenticate(self.group_admin_a)
        datos = {'grupo': self.grupo_b.id, 'nombre': 'Intrusa', 'codigo': 'INT'}
        respuesta = self.client.post('/api/v1/clinicas/', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('grupo', respuesta.data)

    def test_group_admin_crea_clinica_en_su_propio_grupo(self):
        self.client.force_authenticate(self.group_admin_a)
        datos = {
            'grupo': self.grupo_a.id, 'nombre': 'Nueva', 'codigo': 'NUE',
            'especialidades': [self.cardiologia.id],
        }
        respuesta = self.client.post('/api/v1/clinicas/', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

    def test_superadmin_ve_todas_las_clinicas(self):
        self.client.force_authenticate(self.superadmin)
        respuesta = self.client.get('/api/v1/clinicas/')
        self.assertEqual(respuesta.data['count'], 3)

    def test_codigo_duplicado_en_mismo_grupo_devuelve_400(self):
        self.client.force_authenticate(self.superadmin)
        datos = {'grupo': self.grupo_a.id, 'nombre': 'Duplicada', 'codigo': 'ALD'}
        respuesta = self.client.post('/api/v1/clinicas/', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)


class EspecialidadApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.grupo = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.group_admin = CustomUser.objects.create_user(
            username='admin_a', password='clave123', grupo=self.grupo,
        )
        usuarios_services.asignar_rol(usuario=self.group_admin, rol=Roles.GROUP_ADMIN)
        self.sin_rol = CustomUser.objects.create_user(
            username='ana', password='clave123', grupo=self.grupo,
        )

    def test_sin_permiso_no_accede(self):
        self.client.force_authenticate(self.sin_rol)
        respuesta = self.client.get('/api/v1/especialidades/')
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_admin_crud_basico(self):
        self.client.force_authenticate(self.group_admin)
        respuesta = self.client.post(
            '/api/v1/especialidades/', {'nombre': 'Cardiología', 'profesion': 'Cardiólogo'},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

        respuesta = self.client.get('/api/v1/especialidades/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['count'], 1)
