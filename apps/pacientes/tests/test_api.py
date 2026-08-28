"""tests de la api de pacientes: permisos granulares por acción (patients.view/create/
update/delete) y aislamiento multi-tenant por grupo.
"""
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.organizacion.models import Clinica, Grupo
from apps.pacientes.models import Paciente
from apps.pacientes.services import crear_paciente
from apps.usuarios import services as usuarios_services
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles


def _payload(**overrides):
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


class PacienteApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')
        self.clinica_a = Clinica.objects.create(grupo=self.grupo_a, nombre='Aldaia', codigo='ALD')
        self.paciente_a = crear_paciente(grupo=self.grupo_a, **_payload())
        self.paciente_b = crear_paciente(
            grupo=self.grupo_b, **_payload(nhc='NHC002', documento_numero='87654321B'),
        )
        self.superadmin = CustomUser.objects.create_user(
            username='root', password='clave123', is_superuser=True,
        )
        self.group_admin_a = CustomUser.objects.create_user(
            username='admin_a', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(usuario=self.group_admin_a, rol=Roles.GROUP_ADMIN)
        self.doctor_a = CustomUser.objects.create_user(
            username='doc_a', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(
            usuario=self.doctor_a, rol=Roles.DOCTOR, clinica=self.clinica_a,
        )
        self.recepcion_a = CustomUser.objects.create_user(
            username='rec_a', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(
            usuario=self.recepcion_a, rol=Roles.RECEPTIONIST, clinica=self.clinica_a,
        )

    def test_requiere_autenticacion(self):
        respuesta = self.client.get('/api/v1/pacientes/')
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_usuario_de_un_grupo_solo_lista_los_pacientes_de_su_grupo(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.get('/api/v1/pacientes/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        nhcs = {p['nhc'] for p in respuesta.data['results']}
        self.assertEqual(nhcs, {'NHC001'})

    def test_no_resuelve_por_id_directo_un_paciente_de_otro_grupo(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.get(f'/api/v1/pacientes/{self.paciente_b.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_superadmin_ve_todos_los_pacientes(self):
        self.client.force_authenticate(self.superadmin)
        respuesta = self.client.get('/api/v1/pacientes/')
        self.assertEqual(respuesta.data['count'], 2)

    def test_doctor_puede_ver_y_actualizar_pero_no_crear_ni_eliminar(self):
        self.client.force_authenticate(self.doctor_a)
        respuesta = self.client.get('/api/v1/pacientes/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

        respuesta = self.client.patch(
            f'/api/v1/pacientes/{self.paciente_a.pk}/', {'telefono': '600111222'},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

        respuesta = self.client.post('/api/v1/pacientes/', _payload(nhc='NHC003'))
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

        respuesta = self.client.delete(f'/api/v1/pacientes/{self.paciente_a.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_recepcion_puede_crear_pero_no_actualizar_ni_eliminar(self):
        self.client.force_authenticate(self.recepcion_a)
        datos = _payload(nhc='NHC003', documento_numero='11111111C')
        respuesta = self.client.post('/api/v1/pacientes/', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        # el grupo se asigna automáticamente al del usuario, no se expone como elección.
        self.assertNotIn('grupo', respuesta.data)
        self.assertEqual(Paciente.objects.get(nhc='NHC003').grupo, self.grupo_a)

        respuesta = self.client.patch(
            f'/api/v1/pacientes/{self.paciente_a.pk}/', {'telefono': '600111222'},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

        respuesta = self.client.delete(f'/api/v1/pacientes/{self.paciente_a.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_recepcion_no_puede_crear_paciente_en_otro_grupo(self):
        # el campo grupo ni siquiera está disponible para un no-superusuario: no hay forma de
        # colar un grupo ajeno en el payload.
        self.client.force_authenticate(self.recepcion_a)
        datos = _payload(nhc='NHC003', documento_numero='11111111C', grupo=self.grupo_b.id)
        respuesta = self.client.post('/api/v1/pacientes/', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Paciente.objects.get(nhc='NHC003').grupo, self.grupo_a)

    def test_group_admin_puede_desactivar_paciente(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.delete(f'/api/v1/pacientes/{self.paciente_a.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_204_NO_CONTENT)
        self.paciente_a.refresh_from_db()
        self.assertFalse(self.paciente_a.is_active)

    def test_group_admin_crea_paciente_con_nhc_duplicado_devuelve_400(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.post('/api/v1/pacientes/', _payload())
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_busqueda_por_nombre_apellido_documento_o_nhc(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.get('/api/v1/pacientes/', {'search': 'Pérez'})
        self.assertEqual(respuesta.data['count'], 1)
