"""tests de las vistas html de medicos: permisos granulares por acción, aislamiento
multi-tenant por grupo, y gestión de especialidad por clínica.
"""
from django.test import TestCase
from django.urls import reverse

from apps.medicos.models import Medico
from apps.medicos.services import crear_medico
from apps.organizacion.models import Clinica, Especialidad, Grupo
from apps.usuarios import services as usuarios_services
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles


class MedicoVistasTests(TestCase):
    def setUp(self):
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
        self.usuario_nuevo_medico_a = CustomUser.objects.create_user(
            username='nuevo_medico_a', password='clave123', grupo=self.grupo_a,
        )

    def test_anonimo_redirige_al_login(self):
        respuesta = self.client.get(reverse('medicos:medico-list'))
        self.assertRedirects(
            respuesta, f'/login/?next={reverse("medicos:medico-list")}',
        )

    def test_sin_permiso_no_accede(self):
        self.client.force_login(self.sin_rol)
        respuesta = self.client.get(reverse('medicos:medico-list'))
        self.assertEqual(respuesta.status_code, 403)

    def test_group_admin_lista_solo_los_medicos_de_su_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('medicos:medico-list'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(list(respuesta.context['object_list']), [self.medico_a])

    def test_no_resuelve_por_id_directo_un_medico_de_otro_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(
            reverse('medicos:medico-detalle', args=[self.medico_b.pk]),
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_group_admin_crea_medico_sin_elegir_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('medicos:medico-crear'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('grupo', respuesta.context['form'].fields)

        datos = {'usuario': self.usuario_nuevo_medico_a.pk, 'colegiado': 'COL003', 'telefono': ''}
        respuesta = self.client.post(reverse('medicos:medico-crear'), datos)
        self.assertRedirects(respuesta, reverse('medicos:medico-list'))
        creado = Medico.objects.get(colegiado='COL003')
        self.assertEqual(creado.grupo, self.grupo_a)

    def test_doctor_no_puede_crear_ni_editar_ni_dar_de_baja(self):
        self.client.force_login(self.doctor_a)
        respuesta = self.client.get(reverse('medicos:medico-crear'))
        self.assertEqual(respuesta.status_code, 403)
        respuesta = self.client.get(
            reverse('medicos:medico-editar', args=[self.medico_a.pk]),
        )
        self.assertEqual(respuesta.status_code, 403)
        respuesta = self.client.get(
            reverse('medicos:medico-eliminar', args=[self.medico_a.pk]),
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_group_admin_edita_medico_de_su_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.post(
            reverse('medicos:medico-editar', args=[self.medico_a.pk]),
            {'colegiado': 'COL001', 'telefono': '600111222'},
        )
        self.assertRedirects(respuesta, reverse('medicos:medico-list'))
        self.medico_a.refresh_from_db()
        self.assertEqual(self.medico_a.telefono, '600111222')

    def test_baja_es_soft_delete_y_reactivar_lo_revierte(self):
        self.client.force_login(self.group_admin_a)
        url_baja = reverse('medicos:medico-eliminar', args=[self.medico_a.pk])
        respuesta = self.client.post(url_baja)
        self.assertEqual(respuesta.status_code, 302)
        self.medico_a.refresh_from_db()
        self.assertFalse(self.medico_a.is_active)

        url_reactivar = reverse('medicos:medico-reactivar', args=[self.medico_a.pk])
        respuesta = self.client.post(url_reactivar)
        self.assertEqual(respuesta.status_code, 302)
        self.medico_a.refresh_from_db()
        self.assertTrue(self.medico_a.is_active)

    def test_recepcion_no_ve_botones_de_editar_ni_eliminar(self):
        # RECEPTIONIST tiene doctors.view pero no doctors.update/delete: la fila se ve, pero
        # los botones de editar/desactivar no deben aparecer.
        self.client.force_login(self.recepcion_a)
        respuesta = self.client.get(reverse('medicos:medico-list'))
        self.assertContains(respuesta, self.medico_a.colegiado)
        url_editar = reverse('medicos:medico-editar', args=[self.medico_a.pk])
        url_eliminar = reverse('medicos:medico-eliminar', args=[self.medico_a.pk])
        self.assertNotContains(respuesta, f'href="{url_editar}"')
        self.assertNotContains(respuesta, f'hx-get="{url_eliminar}"')

    def test_group_admin_ve_editar_eliminar_y_clinicas(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('medicos:medico-list'))
        url_editar = reverse('medicos:medico-editar', args=[self.medico_a.pk])
        url_eliminar = reverse('medicos:medico-eliminar', args=[self.medico_a.pk])
        url_clinicas = reverse('medicos:medico-clinicas', args=[self.medico_a.pk])
        self.assertContains(respuesta, f'href="{url_editar}"')
        self.assertContains(respuesta, f'hx-get="{url_eliminar}"')
        self.assertContains(respuesta, f'href="{url_clinicas}"')


class MedicoClinicasVistasTests(TestCase):
    """gestión de especialidad por clínica (MedicoClinicaEspecialidad)."""

    def setUp(self):
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.clinica_a = Clinica.objects.create(grupo=self.grupo_a, nombre='Aldaia', codigo='ALD')
        self.especialidad = Especialidad.objects.create(nombre='Cardiología', profesion='Cardiólogo')
        self.usuario_medico_a = CustomUser.objects.create_user(
            username='medico_a_user', password='clave123', grupo=self.grupo_a,
        )
        self.medico_a = crear_medico(
            grupo=self.grupo_a, usuario=self.usuario_medico_a, colegiado='COL001',
        )
        self.group_admin_a = CustomUser.objects.create_user(
            username='admin_a', password='clave123', grupo=self.grupo_a,
        )
        usuarios_services.asignar_rol(usuario=self.group_admin_a, rol=Roles.GROUP_ADMIN)

    def test_group_admin_asigna_y_quita_especialidad(self):
        self.client.force_login(self.group_admin_a)
        url_clinicas = reverse('medicos:medico-clinicas', args=[self.medico_a.pk])
        respuesta = self.client.get(url_clinicas)
        self.assertEqual(respuesta.status_code, 200)

        url_crear = reverse('medicos:medico-clinica-crear', args=[self.medico_a.pk])
        respuesta = self.client.post(
            url_crear, {'clinica': self.clinica_a.pk, 'especialidad': self.especialidad.pk},
        )
        self.assertRedirects(respuesta, url_clinicas)
        asignacion = self.medico_a.asignaciones_clinica.get()
        self.assertEqual(asignacion.clinica, self.clinica_a)

        url_eliminar = reverse(
            'medicos:medico-clinica-eliminar', args=[self.medico_a.pk, asignacion.pk],
        )
        respuesta = self.client.post(url_eliminar)
        self.assertRedirects(respuesta, url_clinicas)
        self.assertEqual(self.medico_a.asignaciones_clinica.count(), 0)


class MedicoAusenciaVistasTests(TestCase):
    """vistas html de ausencias de médicos: listado, detalle, crear/editar en modal,
    baja y reactivar."""

    def setUp(self):
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
        self.sin_rol = CustomUser.objects.create_user(
            username='ana', password='clave123', grupo=self.grupo_a,
        )

        self.ausencia_a = self.medico_a.ausencias.create(
            fecha_inicio='2026-03-01', fecha_fin='2026-03-05',
            motivo='vacaciones', estado='P',
        )
        self.ausencia_b = self.medico_b.ausencias.create(
            fecha_inicio='2026-04-01', fecha_fin='2026-04-03',
            motivo='baja', estado='P',
        )

    def test_anonimo_redirige_al_login(self):
        respuesta = self.client.get(reverse('medicos:ausencia-list'))
        self.assertRedirects(
            respuesta, f'/login/?next={reverse("medicos:ausencia-list")}',
        )

    def test_sin_permiso_no_accede(self):
        self.client.force_login(self.sin_rol)
        respuesta = self.client.get(reverse('medicos:ausencia-list'))
        self.assertEqual(respuesta.status_code, 403)

    def test_group_admin_lista_solo_ausencias_de_su_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('medicos:ausencia-list'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(list(respuesta.context['object_list']), [self.ausencia_a])

    def test_no_resuelve_por_id_directo_una_ausencia_de_otro_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(
            reverse('medicos:ausencia-detalle', args=[self.ausencia_b.pk]),
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_group_admin_crea_ausencia_en_modal(self):
        self.client.force_login(self.group_admin_a)
        # petición HTMX: devuelve fragmento de modal
        respuesta = self.client.get(
            reverse('medicos:ausencia-crear'),
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'hx-post')

        # POST para guardar
        datos = {
            'medico': self.medico_a.pk, 'fecha_inicio': '2026-06-01',
            'fecha_fin': '2026-06-10', 'motivo': 'congreso', 'estado': 'P',
        }
        respuesta = self.client.post(
            reverse('medicos:ausencia-crear'), datos,
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(respuesta.status_code, 204)
        self.medico_a.ausencias.get(fecha_inicio='2026-06-01')

    def test_group_admin_edita_ausencia_en_modal(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(
            reverse('medicos:ausencia-editar', args=[self.ausencia_a.pk]),
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(respuesta.status_code, 200)

        datos = {
            'medico': self.medico_a.pk, 'fecha_inicio': '2026-03-01',
            'fecha_fin': '2026-03-10', 'motivo': 'vacaciones', 'estado': 'A',
        }
        respuesta = self.client.post(
            reverse('medicos:ausencia-editar', args=[self.ausencia_a.pk]),
            datos, HTTP_HX_REQUEST='true',
        )
        self.assertEqual(respuesta.status_code, 204)
        self.ausencia_a.refresh_from_db()
        self.assertEqual(self.ausencia_a.estado, 'A')

    def test_baja_es_soft_delete_y_reactivar_lo_revierte(self):
        self.client.force_login(self.group_admin_a)
        url_baja = reverse('medicos:ausencia-eliminar', args=[self.ausencia_a.pk])
        respuesta = self.client.post(url_baja)
        self.assertEqual(respuesta.status_code, 302)
        self.ausencia_a.refresh_from_db()
        self.assertFalse(self.ausencia_a.is_active)

        url_reactivar = reverse('medicos:ausencia-reactivar', args=[self.ausencia_a.pk])
        respuesta = self.client.post(url_reactivar)
        self.assertEqual(respuesta.status_code, 302)
        self.ausencia_a.refresh_from_db()
        self.assertTrue(self.ausencia_a.is_active)

    def test_doctor_no_puede_crear_ni_editar_ni_dar_de_baja(self):
        self.client.force_login(self.doctor_a)
        respuesta = self.client.get(reverse('medicos:ausencia-crear'))
        self.assertEqual(respuesta.status_code, 403)
        respuesta = self.client.get(
            reverse('medicos:ausencia-editar', args=[self.ausencia_a.pk]),
        )
        self.assertEqual(respuesta.status_code, 403)
        respuesta = self.client.get(
            reverse('medicos:ausencia-eliminar', args=[self.ausencia_a.pk]),
        )
        self.assertEqual(respuesta.status_code, 403)
