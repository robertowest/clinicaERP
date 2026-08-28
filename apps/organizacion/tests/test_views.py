"""tests de las vistas html de organizacion: control de acceso basado en roles/permisos
granulares (apps.usuarios.roles.PERMISOS_POR_ROL), no en is_staff.
"""

from django.test import TestCase
from django.urls import reverse

from apps.organizacion.models import Clinica, Especialidad, Grupo
from apps.usuarios import services as usuarios_services
from apps.usuarios.models import CustomUser
from apps.usuarios.roles import Roles


class GrupoVistasTests(TestCase):
    def setUp(self):
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

    def test_anonimo_redirige_al_login(self):
        respuesta = self.client.get(reverse('organizacion:grupo-list'))
        self.assertRedirects(
            respuesta,
            f'/login/?next={reverse("organizacion:grupo-list")}',
        )

    def test_sin_permiso_no_accede_ni_en_lectura(self):
        self.client.force_login(self.sin_rol)
        respuesta = self.client.get(reverse('organizacion:grupo-list'))
        self.assertEqual(respuesta.status_code, 403)

    def test_group_admin_solo_lista_su_propio_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('organizacion:grupo-list'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(list(respuesta.context['object_list']), [self.grupo_a])

    def test_group_admin_no_resuelve_por_id_directo_el_grupo_de_otro_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(
            reverse('organizacion:grupo-detalle', args=[self.grupo_b.pk]),
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_group_admin_no_puede_crear_grupos_nuevos(self):
        # crear un grupo da de alta un tenant nuevo: sigue siendo exclusivo de superadmin.
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('organizacion:grupo-crear'))
        self.assertEqual(respuesta.status_code, 403)

    def test_group_admin_edita_su_propio_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.post(
            reverse('organizacion:grupo-editar', args=[self.grupo_a.pk]),
            {'nombre': 'Renombrado', 'codigo': 'GRA'},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.grupo_a.refresh_from_db()
        self.assertEqual(self.grupo_a.nombre, 'Renombrado')

    def test_superadmin_lista_y_crea(self):
        self.client.force_login(self.superadmin)
        respuesta = self.client.get(reverse('organizacion:grupo-list'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context['object_list']), 2)

        respuesta = self.client.post(
            reverse('organizacion:grupo-crear'),
            {'nombre': 'Grupo Hera', 'codigo': 'HRA'},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Grupo.objects.filter(codigo='HRA').exists())

    def test_crear_codigo_duplicado_no_crea_y_muestra_error(self):
        # el propio ModelForm ya valida la unicidad de `codigo` (unique=True) antes de
        # llegar a `form_valid`; `services.crear_grupo` cubre el resto de casos (p. ej.
        # una `UniqueConstraint` multi-campo, como la de clínica) igual que en la api.
        self.client.force_login(self.superadmin)
        respuesta = self.client.post(
            reverse('organizacion:grupo-crear'),
            {'nombre': 'Otro', 'codigo': 'GRA'},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['form'].errors.get('codigo'))
        self.assertEqual(Grupo.objects.filter(codigo='GRA').count(), 1)

    def test_baja_es_soft_delete_y_reactivar_lo_revierte(self):
        self.client.force_login(self.group_admin_a)
        url_baja = reverse('organizacion:grupo-eliminar', args=[self.grupo_a.pk])
        respuesta = self.client.post(url_baja)
        self.assertEqual(respuesta.status_code, 302)
        self.grupo_a.refresh_from_db()
        self.assertFalse(self.grupo_a.is_active)

        url_reactivar = reverse('organizacion:grupo-reactivar', args=[self.grupo_a.pk])
        respuesta = self.client.post(url_reactivar)
        self.assertEqual(respuesta.status_code, 302)
        self.grupo_a.refresh_from_db()
        self.assertTrue(self.grupo_a.is_active)


class ClinicaVistasTests(TestCase):
    def setUp(self):
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')
        self.clinica_a1 = Clinica.objects.create(grupo=self.grupo_a, nombre='Aldaia', codigo='ALD')
        self.clinica_a2 = Clinica.objects.create(grupo=self.grupo_a, nombre='Torrent', codigo='TOR')
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
        self.sin_rol = CustomUser.objects.create_user(
            username='ana', password='clave123', grupo=self.grupo_a,
        )

    def test_sin_permiso_no_accede(self):
        self.client.force_login(self.sin_rol)
        respuesta = self.client.get(reverse('organizacion:clinica-list'))
        self.assertEqual(respuesta.status_code, 403)

    def test_group_admin_lista_las_clinicas_de_su_grupo(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('organizacion:clinica-list'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertCountEqual(
            respuesta.context['object_list'], [self.clinica_a1, self.clinica_a2],
        )

    def test_clinic_admin_lista_solo_su_clinica(self):
        self.client.force_login(self.clinic_admin_a1)
        respuesta = self.client.get(reverse('organizacion:clinica-list'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(list(respuesta.context['object_list']), [self.clinica_a1])

    def test_clinic_admin_no_resuelve_por_id_directo_una_clinica_ajena(self):
        self.client.force_login(self.clinic_admin_a1)
        respuesta = self.client.get(
            reverse('organizacion:clinica-detalle', args=[self.clinica_a2.pk]),
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_group_admin_crea_clinica_en_su_propio_grupo(self):
        self.client.force_login(self.group_admin_a)
        datos = {'grupo': self.grupo_a.pk, 'nombre': 'Nueva', 'codigo': 'NUE'}
        respuesta = self.client.post(reverse('organizacion:clinica-crear'), datos)
        self.assertRedirects(respuesta, reverse('organizacion:clinica-list'))
        self.assertTrue(self.grupo_a.clinicas.filter(codigo='NUE').exists())

    def test_group_admin_no_puede_elegir_un_grupo_ajeno_al_crear(self):
        # el queryset del campo `grupo` del form se acota al alcance del usuario: el grupo
        # ajeno ni siquiera aparece como opción válida.
        self.client.force_login(self.group_admin_a)
        datos = {'grupo': self.grupo_b.pk, 'nombre': 'Intrusa', 'codigo': 'INT'}
        respuesta = self.client.post(reverse('organizacion:clinica-crear'), datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['form'].errors.get('grupo'))
        self.assertFalse(Clinica.objects.filter(codigo='INT').exists())

    def test_group_admin_ve_editar_y_desactivar_en_la_tabla(self):
        # GROUP_ADMIN tiene clinics.manage: los botones de editar/desactivar de
        # _acciones_columna.html deben seguir apareciendo (no debe romperse por el cambio
        # de gating de is_staff a permiso granular).
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('organizacion:clinica-list'))
        url_editar = reverse('organizacion:clinica-editar', args=[self.clinica_a1.pk])
        url_eliminar = reverse('organizacion:clinica-eliminar', args=[self.clinica_a1.pk])
        self.assertContains(respuesta, f'href="{url_editar}"')
        self.assertContains(respuesta, f'hx-get="{url_eliminar}"')

    def test_formularios_y_modales_renderizan(self):
        self.client.force_login(self.group_admin_a)
        respuesta = self.client.get(reverse('organizacion:clinica-list'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, self.clinica_a1.nombre)

        respuesta = self.client.get(reverse('organizacion:clinica-crear'))
        self.assertEqual(respuesta.status_code, 200)
        for nombre in ['clinica-detalle', 'clinica-editar', 'clinica-eliminar']:
            respuesta = self.client.get(
                reverse(f'organizacion:{nombre}', args=[self.clinica_a1.pk]),
            )
            self.assertEqual(respuesta.status_code, 200, nombre)


class EspecialidadVistasTests(TestCase):
    def setUp(self):
        self.grupo = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.group_admin = CustomUser.objects.create_user(
            username='admin_a', password='clave123', grupo=self.grupo,
        )
        usuarios_services.asignar_rol(usuario=self.group_admin, rol=Roles.GROUP_ADMIN)
        self.sin_rol = CustomUser.objects.create_user(
            username='ana', password='clave123', grupo=self.grupo,
        )
        self.cardiologia = Especialidad.objects.create(nombre='Cardiología')

    def test_sin_permiso_no_accede(self):
        self.client.force_login(self.sin_rol)
        respuesta = self.client.get(reverse('organizacion:especialidad-list'))
        self.assertEqual(respuesta.status_code, 403)

    def test_group_admin_edita_especialidad(self):
        self.client.force_login(self.group_admin)
        url = reverse('organizacion:especialidad-editar', args=[self.cardiologia.pk])
        respuesta = self.client.post(
            url, {'nombre': 'Cardiología intervencionista', 'profesion': 'Cardiólogo'},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.cardiologia.refresh_from_db()
        self.assertEqual(self.cardiologia.nombre, 'Cardiología intervencionista')

    def test_formularios_y_modales_renderizan(self):
        self.client.force_login(self.group_admin)
        respuesta = self.client.get(reverse('organizacion:especialidad-crear'))
        self.assertEqual(respuesta.status_code, 200)
        for nombre in ['especialidad-detalle', 'especialidad-editar', 'especialidad-eliminar']:
            respuesta = self.client.get(
                reverse(f'organizacion:{nombre}', args=[self.cardiologia.pk]),
            )
            self.assertEqual(respuesta.status_code, 200, nombre)
