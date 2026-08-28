"""test de integración cross-app (fase 7, ver arquitectura.md §7): un mismo escenario con
`organizacion` + `usuarios` + `pacientes` + `medicos` a la vez, autenticado vía jwt real
(login → token → peticiones), para demostrar el aislamiento multi-tenant de punta a punta
tal y como lo usaría un cliente real de la api (a diferencia de los tests por-app, que no
cruzan `pacientes` y `medicos` en un mismo escenario).
"""
from rest_framework import status
from rest_framework.test import APITestCase

from apps.medicos.services import asignar_clinica_especialidad, crear_medico
from apps.organizacion.models import Clinica, Especialidad, Grupo
from apps.pacientes.services import crear_paciente
from apps.usuarios import services as usuarios_services
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles

PASSWORD = 'clave123'


class AislamientoMultiTenantIntegracionTests(APITestCase):
    def setUp(self):
        # dos grupos completos e independientes: clínica, especialidad, usuario con rol,
        # paciente y médico — el escenario íntegro que un cliente real de la api recorrería.
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')

        self.clinica_a = Clinica.objects.create(grupo=self.grupo_a, nombre='Aldaia', codigo='ALD')
        self.clinica_b = Clinica.objects.create(grupo=self.grupo_b, nombre='Torrent', codigo='TOR')

        self.especialidad = Especialidad.objects.create(nombre='Cardiología', profesion='Cardiólogo')

        self.paciente_a = crear_paciente(
            grupo=self.grupo_a, nhc='NHC001', nombre='Juan', apellido='Pérez',
            documento_tipo='dni', documento_numero='11111111A',
            fecha_nacimiento='1980-01-01', sexo='M',
        )
        self.paciente_b = crear_paciente(
            grupo=self.grupo_b, nhc='NHC001', nombre='Ana', apellido='Ruiz',
            documento_tipo='dni', documento_numero='22222222B',
            fecha_nacimiento='1985-01-01', sexo='F',
        )

        self.usuario_medico_a = CustomUser.objects.create_user(
            username='doctor_a_user', password=PASSWORD, grupo=self.grupo_a,
        )
        self.medico_a = crear_medico(
            grupo=self.grupo_a, usuario=self.usuario_medico_a, colegiado='COL001',
        )
        asignar_clinica_especialidad(
            medico=self.medico_a, clinica=self.clinica_a, especialidad=self.especialidad,
        )
        self.usuario_medico_b = CustomUser.objects.create_user(
            username='doctor_b_user', password=PASSWORD, grupo=self.grupo_b,
        )
        self.medico_b = crear_medico(
            grupo=self.grupo_b, usuario=self.usuario_medico_b, colegiado='COL001',
        )

        self.admin_a = CustomUser.objects.create_user(
            username='admin_a', password=PASSWORD, grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(usuario=self.admin_a, rol=Roles.GROUP_ADMIN)

    def _login(self, username):
        respuesta = self.client.post(
            '/api/v1/auth/token/', {'username': username, 'password': PASSWORD},
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        return respuesta.data['access']

    def _autenticar(self, username):
        token = self._login(username)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_login_me_pacientes_y_medicos_de_un_grupo_no_filtran_al_otro(self):
        self._autenticar('admin_a')

        respuesta = self.client.get('/api/v1/auth/me/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['group']['codigo'], 'GRA')

        respuesta = self.client.get('/api/v1/pacientes/')
        nhcs_visibles = {p['id'] for p in respuesta.data['results']}
        self.assertEqual(nhcs_visibles, {self.paciente_a.id})

        respuesta = self.client.get('/api/v1/medicos/')
        medicos_visibles = {m['id'] for m in respuesta.data['results']}
        self.assertEqual(medicos_visibles, {self.medico_a.id})

    def test_no_resuelve_por_id_directo_recursos_de_otro_grupo(self):
        self._autenticar('admin_a')

        respuesta = self.client.get(f'/api/v1/pacientes/{self.paciente_b.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

        respuesta = self.client.get(f'/api/v1/medicos/{self.medico_b.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

        # y sí resuelve los de su propio grupo:
        respuesta = self.client.get(f'/api/v1/pacientes/{self.paciente_a.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        respuesta = self.client.get(f'/api/v1/medicos/{self.medico_a.pk}/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_sin_token_todo_el_flujo_requiere_autenticacion(self):
        for url in ('/api/v1/auth/me/', '/api/v1/pacientes/', '/api/v1/medicos/'):
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED, url)
