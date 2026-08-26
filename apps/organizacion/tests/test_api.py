"""tests de la api de organizacion (sin depender de fase 4: se usa force_authenticate)."""
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.organizacion.models import Especialidad, Grupo
from apps.usuarios.models import CustomUser


class GrupoApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = CustomUser.objects.create_user(username='ana', password='clave123')
        self.staff = CustomUser.objects.create_user(
            username='root', password='clave123', is_staff=True,
        )

    def test_requiere_autenticacion(self):
        respuesta = self.client.get('/api/v1/grupos/')
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_staff_no_puede_acceder(self):
        self.client.force_authenticate(self.usuario)
        respuesta = self.client.get('/api/v1/grupos/')
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_puede_crear_y_listar(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.post('/api/v1/grupos/', {'nombre': 'Grupo Atenea', 'codigo': 'ATN'})
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

        respuesta = self.client.get('/api/v1/grupos/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['count'], 1)

    def test_crear_codigo_duplicado_devuelve_400(self):
        Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')
        self.client.force_authenticate(self.staff)
        respuesta = self.client.post('/api/v1/grupos/', {'nombre': 'Otro', 'codigo': 'ATN'})
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)


class ClinicaApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = CustomUser.objects.create_user(username='ana', password='clave123')
        self.staff = CustomUser.objects.create_user(
            username='root', password='clave123', is_staff=True,
        )
        self.grupo = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')
        self.cardiologia = Especialidad.objects.create(nombre='Cardiología')

    def test_lectura_permitida_a_cualquier_autenticado(self):
        self.client.force_authenticate(self.usuario)
        respuesta = self.client.get('/api/v1/clinicas/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_escritura_solo_staff(self):
        self.client.force_authenticate(self.usuario)
        datos = {'grupo': self.grupo.id, 'nombre': 'Clínica Aldaia', 'codigo': 'ALD'}
        respuesta = self.client.post('/api/v1/clinicas/', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_crea_clinica_con_especialidades(self):
        self.client.force_authenticate(self.staff)
        datos = {
            'grupo': self.grupo.id,
            'nombre': 'Clínica Aldaia',
            'codigo': 'ALD',
            'especialidades': [self.cardiologia.id],
        }
        respuesta = self.client.post('/api/v1/clinicas/', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data['especialidades'], [self.cardiologia.id])

    def test_codigo_duplicado_en_mismo_grupo_devuelve_400(self):
        self.client.force_authenticate(self.staff)
        datos = {'grupo': self.grupo.id, 'nombre': 'Clínica Aldaia', 'codigo': 'ALD'}
        self.client.post('/api/v1/clinicas/', datos)
        respuesta = self.client.post('/api/v1/clinicas/', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_busqueda_y_ordenacion(self):
        self.client.force_authenticate(self.staff)
        datos = {'grupo': self.grupo.id, 'nombre': 'Clínica Aldaia', 'codigo': 'ALD'}
        self.client.post('/api/v1/clinicas/', datos)
        respuesta = self.client.get('/api/v1/clinicas/', {'search': 'Aldaia', 'ordering': 'nombre'})
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['count'], 1)


class EspecialidadApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = CustomUser.objects.create_user(username='ana', password='clave123')
        self.staff = CustomUser.objects.create_user(
            username='root', password='clave123', is_staff=True,
        )

    def test_crud_basico(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.post(
            '/api/v1/especialidades/', {'nombre': 'Cardiología', 'profesion': 'Cardiólogo'},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.usuario)
        respuesta = self.client.get('/api/v1/especialidades/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['count'], 1)
