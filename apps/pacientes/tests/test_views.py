"""tests de las vistas html de pacientes: permisos granulares por acción y aislamiento
multi-tenant por grupo.
"""
from django.test import TestCase
from django.urls import reverse

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


class PacienteVistasTests(TestCase):
    def setUp(self):
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')
        self.clinica_a = Clinica.objects.create(grupo=self.grupo_a, nombre='Aldaia', codigo='ALD')
        self.paciente_a = crear_paciente(grupo=self.grupo_a, **_payload())
        self.paciente_b = crear_paciente(
            grupo=self.grupo_b, **_payload(nhc='NHC002', documento_numero='87654321B'),
        )
        self.group_admin_a = CustomUser.objects.create_user(
            username='admin_a', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(usuario=self.group_admin_a, rol=Roles.GROUP_ADMIN)
        self.recepcion_a = CustomUser.objects.create_user(
            username='rec_a', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(
            usuario=self.recepcion_a, rol=Roles.RECEPTIONIST, clinica=self.clinica_a,
        )
        self.doctor_a = CustomUser.objects.create_user(
            username='doc_a', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(
            usuario=self.doctor_a, rol=Roles.DOCTOR, clinica=self.clinica_a,
        )
        self.sin_rol = CustomUser.objects.create_user(
            username='ana', password='clave123', grupo=self.grupo_a,
        )

    def test_anonimo_redirige_al_login(self):
        respuesta = self.client.get(reverse('pacientes:paciente-list'))
        self.assertRedirects(
            respuesta, f'/login/?next={reverse("pacientes:paciente-list")}',
        )

    def test_sin_permiso_no_accede(self):
        self.client.force_login(self.sin_rol)
        respuesta = self.client.get(reverse('pacientes:paciente-list'))
        self.assertEqual(respuesta.status_code, 403)

    def test_group_admin_lista_solo_los_pacientes_de_su_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('pacientes:paciente-list'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(list(respuesta.context['object_list']), [self.paciente_a])

    def test_no_resuelve_por_id_directo_un_paciente_de_otro_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(
            reverse('pacientes:paciente-detalle', args=[self.paciente_b.pk]),
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_group_admin_crea_paciente_sin_elegir_grupo_no_disponible_para_su_rol(self):
        # PermisoRequeridoMixin ya exige patients.create; group_admin lo tiene y el campo
        # grupo está oculto (se asigna automáticamente al de su propio usuario).
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('pacientes:paciente-crear'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('grupo', respuesta.context['form'].fields)

        datos = _payload(nhc='NHC003', documento_numero='11111111C')
        respuesta = self.client.post(reverse('pacientes:paciente-crear'), datos)
        self.assertRedirects(respuesta, reverse('pacientes:paciente-list'))
        creado = Paciente.objects.get(nhc='NHC003')
        self.assertEqual(creado.grupo, self.grupo_a)

    def test_recepcion_no_puede_editar_ni_dar_de_baja(self):
        self.client.force_login(self.recepcion_a)
        respuesta = self.client.get(
            reverse('pacientes:paciente-editar', args=[self.paciente_a.pk]),
        )
        self.assertEqual(respuesta.status_code, 403)
        respuesta = self.client.get(
            reverse('pacientes:paciente-eliminar', args=[self.paciente_a.pk]),
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_group_admin_edita_paciente_de_su_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.post(
            reverse('pacientes:paciente-editar', args=[self.paciente_a.pk]),
            {**_payload(), 'telefono': '600111222'},
        )
        self.assertRedirects(respuesta, reverse('pacientes:paciente-list'))
        self.paciente_a.refresh_from_db()
        self.assertEqual(self.paciente_a.telefono, '600111222')

    def test_baja_es_soft_delete_y_reactivar_lo_revierte(self):
        self.client.force_login(self.group_admin_a)
        url_baja = reverse('pacientes:paciente-eliminar', args=[self.paciente_a.pk])
        respuesta = self.client.post(url_baja)
        self.assertEqual(respuesta.status_code, 302)
        self.paciente_a.refresh_from_db()
        self.assertFalse(self.paciente_a.is_active)

        url_reactivar = reverse('pacientes:paciente-reactivar', args=[self.paciente_a.pk])
        respuesta = self.client.post(url_reactivar)
        self.assertEqual(respuesta.status_code, 302)
        self.paciente_a.refresh_from_db()
        self.assertTrue(self.paciente_a.is_active)

    def test_formularios_y_modales_renderizan(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('pacientes:paciente-list'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, self.paciente_a.nhc)

        for nombre in ['paciente-detalle', 'paciente-editar', 'paciente-eliminar']:
            respuesta = self.client.get(
                reverse(f'pacientes:{nombre}', args=[self.paciente_a.pk]),
            )
            self.assertEqual(respuesta.status_code, 200, nombre)

    def test_recepcion_no_ve_botones_de_editar_ni_eliminar(self):
        # RECEPTIONIST tiene patients.view+create pero no patients.update/delete: la fila se
        # ve, pero los botones de editar/desactivar no deben aparecer (ver
        # templates/crud/_acciones_columna.html).
        self.client.force_login(self.recepcion_a)
        respuesta = self.client.get(reverse('pacientes:paciente-list'))
        self.assertContains(respuesta, self.paciente_a.nhc)
        url_editar = reverse('pacientes:paciente-editar', args=[self.paciente_a.pk])
        url_eliminar = reverse('pacientes:paciente-eliminar', args=[self.paciente_a.pk])
        self.assertNotContains(respuesta, f'hx-get="{url_editar}"')
        self.assertNotContains(respuesta, f'hx-get="{url_eliminar}"')

    def test_doctor_ve_editar_pero_no_eliminar(self):
        # DOCTOR tiene patients.view+update pero no patients.delete: ve "Editar" pero no
        # "Desactivar".
        self.client.force_login(self.doctor_a)
        respuesta = self.client.get(reverse('pacientes:paciente-list'))
        url_editar = reverse('pacientes:paciente-editar', args=[self.paciente_a.pk])
        url_eliminar = reverse('pacientes:paciente-eliminar', args=[self.paciente_a.pk])
        self.assertContains(respuesta, f'href="{url_editar}"')
        self.assertNotContains(respuesta, f'hx-get="{url_eliminar}"')

    def test_group_admin_ve_editar_y_eliminar(self):
        # GROUP_ADMIN tiene patients.update/delete: sigue viendo ambos botones.
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('pacientes:paciente-list'))
        url_editar = reverse('pacientes:paciente-editar', args=[self.paciente_a.pk])
        url_eliminar = reverse('pacientes:paciente-eliminar', args=[self.paciente_a.pk])
        self.assertContains(respuesta, f'href="{url_editar}"')
        self.assertContains(respuesta, f'hx-get="{url_eliminar}"')
