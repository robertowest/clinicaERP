"""tests de las vistas html de organizacion (sin depender de fase 4: se usa is_staff)."""

from django.test import TestCase
from django.urls import reverse

from apps.organizacion.models import Especialidad, Grupo
from apps.usuarios.models import CustomUser


class GrupoVistasTests(TestCase):
    def setUp(self):
        self.usuario = CustomUser.objects.create_user(username='ana', password='clave123')
        self.staff = CustomUser.objects.create_user(
            username='root',
            password='clave123',
            is_staff=True,
        )
        self.grupo = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')

    def test_anonimo_redirige_al_login(self):
        respuesta = self.client.get(reverse('organizacion:grupo-list'))
        self.assertRedirects(
            respuesta,
            f'/login/?next={reverse("organizacion:grupo-list")}',
        )

    def test_no_staff_no_accede_ni_en_lectura(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('organizacion:grupo-list'))
        self.assertEqual(respuesta.status_code, 403)

    def test_staff_lista_y_crea(self):
        self.client.force_login(self.staff)
        respuesta = self.client.get(reverse('organizacion:grupo-list'))
        self.assertEqual(respuesta.status_code, 200)

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
        self.client.force_login(self.staff)
        respuesta = self.client.post(
            reverse('organizacion:grupo-crear'),
            {'nombre': 'Otro', 'codigo': 'ATN'},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['form'].errors.get('codigo'))
        self.assertEqual(Grupo.objects.filter(codigo='ATN').count(), 1)

    def test_formularios_y_modales_renderizan(self):
        # cubre que crud/form_modal.html, crud/detail_modal.html y
        # crud/confirm_delete_modal.html no tengan errores de plantilla.
        self.client.force_login(self.staff)
        for nombre in ['grupo-crear']:
            respuesta = self.client.get(reverse(f'organizacion:{nombre}'))
            self.assertEqual(respuesta.status_code, 200, nombre)
        for nombre in ['grupo-detalle', 'grupo-editar', 'grupo-eliminar']:
            respuesta = self.client.get(reverse(f'organizacion:{nombre}', args=[self.grupo.pk]))
            self.assertEqual(respuesta.status_code, 200, nombre)

    def test_baja_es_soft_delete_y_reactivar_lo_revierte(self):
        self.client.force_login(self.staff)
        url_baja = reverse('organizacion:grupo-eliminar', args=[self.grupo.pk])
        respuesta = self.client.post(url_baja)
        self.assertEqual(respuesta.status_code, 302)
        self.grupo.refresh_from_db()
        self.assertFalse(self.grupo.is_active)

        url_reactivar = reverse('organizacion:grupo-reactivar', args=[self.grupo.pk])
        respuesta = self.client.post(url_reactivar)
        self.assertEqual(respuesta.status_code, 302)
        self.grupo.refresh_from_db()
        self.assertTrue(self.grupo.is_active)


class ClinicaVistasTests(TestCase):
    def setUp(self):
        self.usuario = CustomUser.objects.create_user(username='ana', password='clave123')
        self.staff = CustomUser.objects.create_user(
            username='root',
            password='clave123',
            is_staff=True,
        )
        self.grupo = Grupo.objects.create(nombre='Grupo Atenea', codigo='ATN')

    def test_lectura_permitida_a_cualquier_autenticado(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('organizacion:clinica-list'))
        self.assertEqual(respuesta.status_code, 200)

    def test_escritura_solo_staff(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('organizacion:clinica-crear'))
        self.assertEqual(respuesta.status_code, 403)

    def test_staff_crea_clinica_en_pagina_completa(self):
        self.client.force_login(self.staff)
        datos = {'grupo': self.grupo.pk, 'nombre': 'Clínica Aldaia', 'codigo': 'ALD'}
        respuesta = self.client.post(reverse('organizacion:clinica-crear'), datos)
        self.assertRedirects(respuesta, reverse('organizacion:clinica-list'))
        self.assertTrue(self.grupo.clinicas.filter(codigo='ALD').exists())

    def test_formularios_y_modales_renderizan(self):
        self.client.force_login(self.staff)
        datos = {'grupo': self.grupo.pk, 'nombre': 'Clínica Aldaia', 'codigo': 'ALD'}
        self.client.post(reverse('organizacion:clinica-crear'), datos)
        clinica = self.grupo.clinicas.get(codigo='ALD')

        respuesta = self.client.get(reverse('organizacion:clinica-list'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, clinica.nombre)

        respuesta = self.client.get(reverse('organizacion:clinica-crear'))
        self.assertEqual(respuesta.status_code, 200)
        for nombre in ['clinica-detalle', 'clinica-editar', 'clinica-eliminar']:
            respuesta = self.client.get(reverse(f'organizacion:{nombre}', args=[clinica.pk]))
            self.assertEqual(respuesta.status_code, 200, nombre)


class EspecialidadVistasTests(TestCase):
    def setUp(self):
        self.usuario = CustomUser.objects.create_user(username='ana', password='clave123')
        self.staff = CustomUser.objects.create_user(
            username='root',
            password='clave123',
            is_staff=True,
        )
        self.cardiologia = Especialidad.objects.create(nombre='Cardiología')

    def test_lectura_permitida_a_cualquier_autenticado(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('organizacion:especialidad-list'))
        self.assertEqual(respuesta.status_code, 200)

    def test_staff_edita_especialidad(self):
        self.client.force_login(self.staff)
        url = reverse('organizacion:especialidad-editar', args=[self.cardiologia.pk])
        respuesta = self.client.post(
            url, {'nombre': 'Cardiología intervencionista', 'profesion': 'Cardiólogo'},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.cardiologia.refresh_from_db()
        self.assertEqual(self.cardiologia.nombre, 'Cardiología intervencionista')

    def test_formularios_y_modales_renderizan(self):
        self.client.force_login(self.staff)
        respuesta = self.client.get(reverse('organizacion:especialidad-crear'))
        self.assertEqual(respuesta.status_code, 200)
        for nombre in ['especialidad-detalle', 'especialidad-editar', 'especialidad-eliminar']:
            respuesta = self.client.get(
                reverse(f'organizacion:{nombre}', args=[self.cardiologia.pk]),
            )
            self.assertEqual(respuesta.status_code, 200, nombre)
