"""tests de la api de usuarios: jwt (login/refresh) y /auth/me/ (prompt.md §13)."""
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.organizacion.models import Clinica, Grupo
from apps.usuarios import services
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles


class JWTAuthTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = CustomUser.objects.create_user(username='ana', password='clave-larga-123')

    def test_login_devuelve_access_y_refresh(self):
        respuesta = self.client.post(
            '/api/v1/auth/token/', {'username': 'ana', 'password': 'clave-larga-123'},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIn('access', respuesta.data)
        self.assertIn('refresh', respuesta.data)

    def test_login_con_password_incorrecta_falla(self):
        respuesta = self.client.post(
            '/api/v1/auth/token/', {'username': 'ana', 'password': 'incorrecta'},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_devuelve_nuevo_access(self):
        respuesta = self.client.post(
            '/api/v1/auth/token/', {'username': 'ana', 'password': 'clave-larga-123'},
        )
        respuesta = self.client.post(
            '/api/v1/auth/token/refresh/', {'refresh': respuesta.data['refresh']},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIn('access', respuesta.data)


class MeApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.grupo = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')
        self.clinica = Clinica.objects.create(grupo=self.grupo, nombre='Aldaia', codigo='ALD')
        self.usuario = CustomUser.objects.create_user(
            username='ana', password='clave123', email='ana@example.com', grupo=self.grupo,
        )
        services.asignar_rol(usuario=self.usuario, rol=Roles.DOCTOR, clinica=self.clinica)

    def test_requiere_autenticacion(self):
        respuesta = self.client.get('/api/v1/auth/me/')
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_devuelve_usuario_grupo_clinicas_y_roles(self):
        self.client.force_authenticate(self.usuario)
        respuesta = self.client.get('/api/v1/auth/me/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['username'], 'ana')
        self.assertEqual(respuesta.data['group']['codigo'], 'ATN')
        self.assertEqual(len(respuesta.data['clinics']), 1)
        self.assertEqual(respuesta.data['clinics'][0]['codigo'], 'ALD')
        self.assertEqual(respuesta.data['clinics'][0]['rol'], Roles.DOCTOR)
        self.assertEqual(respuesta.data['roles'], [Roles.DOCTOR])

    def test_usuario_sin_grupo_devuelve_group_null(self):
        superadmin = CustomUser.objects.create_user(
            username='root', password='clave123', is_staff=True,
        )
        self.client.force_authenticate(superadmin)
        respuesta = self.client.get('/api/v1/auth/me/')
        self.assertIsNone(respuesta.data['group'])
        self.assertEqual(respuesta.data['clinics'], [])


class UsuarioApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = CustomUser.objects.create_user(username='ana', password='clave123')
        self.staff = CustomUser.objects.create_user(
            username='root', password='clave123', is_staff=True,
        )

    def test_no_staff_no_puede_acceder(self):
        self.client.force_authenticate(self.usuario)
        respuesta = self.client.get('/api/v1/usuarios/')
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_puede_crear_usuario(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.post(
            '/api/v1/usuarios/', {'username': 'luis', 'password': 'clave-larga-123'},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        creado = CustomUser.objects.get(username='luis')
        self.assertTrue(creado.check_password('clave-larga-123'))

    def test_crear_sin_password_devuelve_400(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.post('/api/v1/usuarios/', {'username': 'luis'})
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_username_duplicado_devuelve_400(self):
        self.client.force_authenticate(self.staff)
        respuesta = self.client.post(
            '/api/v1/usuarios/', {'username': 'ana', 'password': 'clave-larga-123'},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
