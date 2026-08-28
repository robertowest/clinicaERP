"""tests de la api de medicos: permisos granulares por acción (doctors.view/create/
update/delete) y aislamiento multi-tenant por grupo.
"""
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.medicos.models import Medico
from apps.medicos.services import crear_medico
from apps.organizacion.models import Clinica, Grupo
from apps.usuarios import services as usuarios_services
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles


class MedicoApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')
        self.clinica_a = Clinica.objects.create(grupo=self.grupo_a, nombre='Aldaia', codigo='ALD')

        self.usuario_medico_a = CustomUser.objects.create_user(
            username='medico_a_user', password='clave123', grupo=self.grupo_a,
        )
        self.usuario_medico_b = CustomUser.objects.create_user(
            username='medico_b_user', password='clave123', grupo=self.grupo_b,
        )
        self.medico_a = crear_medico(
            grupo=self.grupo_a, usuario=self.usuario_medico_a, colegiado='COL001',
        )
        self.medico_b = crear_medico(
            grupo=self.grupo_b, usuario=self.usuario_medico_b, colegiado='COL001',
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
        self.usuario_nuevo_medico_a = CustomUser.objects.create_user(
            username='nuevo_medico_a', password='clave123', grupo=self.grupo_a,
        )

    def test_requiere_autenticacion(self):
        respuesta = self.client.get('/api/v1/medicos/')
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_usuario_de_un_grupo_solo_lista_los_medicos_de_su_grupo(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.get('/api/v1/medicos/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        colegiados = {(m['colegiado'], m['grupo_nombre']) for m in respuesta.data['results']}
        self.assertEqual(colegiados, {('COL001', 'Grupo A')})

    def test_no_resuelve_por_id_directo_un_medico_de_otro_grupo(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.get(f'/api/v1/medicos/{self.medico_b.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_superadmin_ve_todos_los_medicos(self):
        self.client.force_authenticate(self.superadmin)
        respuesta = self.client.get('/api/v1/medicos/')
        self.assertEqual(respuesta.data['count'], 2)

    def test_doctor_puede_ver_pero_no_crear_actualizar_ni_eliminar(self):
        self.client.force_authenticate(self.doctor_a)
        respuesta = self.client.get('/api/v1/medicos/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

        respuesta = self.client.post(
            '/api/v1/medicos/',
            {'usuario': self.usuario_nuevo_medico_a.id, 'colegiado': 'COL003'},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

        respuesta = self.client.patch(
            f'/api/v1/medicos/{self.medico_a.pk}/', {'telefono': '600111222'},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

        respuesta = self.client.delete(f'/api/v1/medicos/{self.medico_a.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_admin_crea_medico_sin_elegir_grupo(self):
        self.client.force_authenticate(self.group_admin_a)
        datos = {'usuario': self.usuario_nuevo_medico_a.id, 'colegiado': 'COL003'}
        respuesta = self.client.post('/api/v1/medicos/', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('grupo', respuesta.data)
        self.assertEqual(Medico.objects.get(colegiado='COL003').grupo, self.grupo_a)

    def test_group_admin_no_puede_crear_medico_en_otro_grupo(self):
        # el campo grupo ni siquiera está disponible para un no-superusuario: no hay forma de
        # colar un grupo ajeno en el payload.
        self.client.force_authenticate(self.group_admin_a)
        datos = {
            'usuario': self.usuario_nuevo_medico_a.id, 'colegiado': 'COL003',
            'grupo': self.grupo_b.id,
        }
        respuesta = self.client.post('/api/v1/medicos/', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Medico.objects.get(colegiado='COL003').grupo, self.grupo_a)

    def test_group_admin_puede_desactivar_medico(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.delete(f'/api/v1/medicos/{self.medico_a.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_204_NO_CONTENT)
        self.medico_a.refresh_from_db()
        self.assertFalse(self.medico_a.is_active)

    def test_group_admin_crea_medico_con_colegiado_duplicado_devuelve_400(self):
        self.client.force_authenticate(self.group_admin_a)
        datos = {'usuario': self.usuario_nuevo_medico_a.id, 'colegiado': 'COL001'}
        respuesta = self.client.post('/api/v1/medicos/', datos)
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_busqueda_por_colegiado(self):
        self.client.force_authenticate(self.group_admin_a)
        respuesta = self.client.get('/api/v1/medicos/', {'search': 'COL001'})
        self.assertEqual(respuesta.data['count'], 1)
