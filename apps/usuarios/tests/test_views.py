"""tests de las vistas html de usuarios."""
from django.test import TestCase
from django.urls import reverse

from apps.organizacion.models import Clinica, Grupo
from apps.usuarios import services
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles


class LoginViewTests(TestCase):
    def setUp(self):
        CustomUser.objects.create_user(username='ana', password='clave-larga-123')

    def test_login_correcto_redirige_a_home(self):
        respuesta = self.client.post(
            reverse('login'), {'username': 'ana', 'password': 'clave-larga-123'},
        )
        self.assertRedirects(respuesta, '/')

    def test_login_incorrecto_no_autentica(self):
        respuesta = self.client.post(reverse('login'), {'username': 'ana', 'password': 'mala'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.wsgi_request.user.is_authenticated)


class UsuarioListViewTests(TestCase):
    def setUp(self):
        self.usuario = CustomUser.objects.create_user(username='ana', password='clave123')
        self.staff = CustomUser.objects.create_user(
            username='root', password='clave123', is_staff=True,
        )

    def test_anonimo_redirige_al_login(self):
        respuesta = self.client.get(reverse('usuarios:usuario-list'))
        self.assertRedirects(respuesta, f'/login/?next={reverse("usuarios:usuario-list")}')

    def test_no_staff_no_accede(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('usuarios:usuario-list'))
        self.assertEqual(respuesta.status_code, 403)

    def test_staff_ve_el_listado(self):
        self.client.force_login(self.staff)
        respuesta = self.client.get(reverse('usuarios:usuario-list'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'ana')


class UsuarioCreateViewTests(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username='root', password='clave123', is_staff=True,
        )
        self.client.force_login(self.staff)

    def test_crea_usuario(self):
        respuesta = self.client.post(
            reverse('usuarios:usuario-crear'),
            {
                'username': 'luis', 'email': '', 'first_name': '', 'last_name': '',
                'password1': 'clave-larga-123', 'password2': 'clave-larga-123',
            },
        )
        self.assertRedirects(respuesta, reverse('usuarios:usuario-list'))
        self.assertTrue(CustomUser.objects.filter(username='luis').exists())

    def test_passwords_distintas_no_crea_usuario(self):
        respuesta = self.client.post(
            reverse('usuarios:usuario-crear'),
            {
                'username': 'luis', 'password1': 'clave-larga-123', 'password2': 'otra-distinta',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(username='luis').exists())


class UsuarioAccesosViewTests(TestCase):
    def setUp(self):
        self.staff = CustomUser.objects.create_user(
            username='root', password='clave123', is_staff=True,
        )
        self.grupo = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')
        self.clinica = Clinica.objects.create(grupo=self.grupo, nombre='Aldaia', codigo='ALD')
        self.usuario = CustomUser.objects.create_user(
            username='ana', password='clave123', grupo=self.grupo,
        )
        self.client.force_login(self.staff)

    def test_asigna_rol_a_clinica(self):
        respuesta = self.client.post(
            reverse('usuarios:usuario-acceso-crear', args=[self.usuario.pk]),
            {'clinica': self.clinica.pk, 'rol': Roles.DOCTOR},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(
            services.listar_asignaciones(usuario=self.usuario).filter(clinica=self.clinica).exists(),
        )

    def test_elimina_acceso(self):
        asignacion = services.asignar_rol(
            usuario=self.usuario, rol=Roles.DOCTOR, clinica=self.clinica,
        )
        respuesta = self.client.post(
            reverse('usuarios:usuario-acceso-eliminar', args=[self.usuario.pk, asignacion.pk]),
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(services.listar_asignaciones(usuario=self.usuario).filter(pk=asignacion.pk).exists())
