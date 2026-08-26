"""tests de los modelos de usuarios."""
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.organizacion.models import Grupo
from apps.usuarios.models import CustomUser, UsuarioClinica
from apps.usuarios.roles import Roles


class CustomUserModelTests(TestCase):
    def test_grupo_es_opcional(self):
        usuario = CustomUser.objects.create_user(username='ana', password='clave123')
        self.assertIsNone(usuario.grupo)

    def test_str_usa_nombre_completo_o_username(self):
        usuario = CustomUser.objects.create_user(
            username='ana', password='clave123', first_name='Ana', last_name='Ruiz',
        )
        self.assertEqual(str(usuario), 'Ana Ruiz')
        usuario.first_name = usuario.last_name = ''
        self.assertEqual(str(usuario), 'ana')


class UsuarioClinicaModelTests(TestCase):
    def setUp(self):
        self.grupo = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')
        self.usuario = CustomUser.objects.create_user(
            username='ana', password='clave123', grupo=self.grupo,
        )

    def test_permite_clinica_nula_para_rol_de_grupo(self):
        asignacion = UsuarioClinica.objects.create(usuario=self.usuario, rol=Roles.GROUP_ADMIN)
        self.assertIsNone(asignacion.clinica)

    def test_unique_constraint_usuario_clinica(self):
        from apps.organizacion.models import Clinica

        clinica = Clinica.objects.create(grupo=self.grupo, nombre='Aldaia', codigo='ALD')
        UsuarioClinica.objects.create(usuario=self.usuario, clinica=clinica, rol=Roles.DOCTOR)
        with self.assertRaises(IntegrityError), transaction.atomic():
            UsuarioClinica.objects.create(
                usuario=self.usuario, clinica=clinica, rol=Roles.CLINIC_ADMIN,
            )
