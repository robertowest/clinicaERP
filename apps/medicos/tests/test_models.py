"""tests de constraints y comportamiento de Medico/MedicoClinicaEspecialidad."""
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.medicos import services
from apps.medicos.models import Medico, MedicoClinicaEspecialidad
from apps.organizacion.models import Clinica, Especialidad, Grupo
from apps.usuarios.models import CustomUser


class MedicoModelTests(TestCase):
    def setUp(self):
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.grupo_b = Grupo.objects.create(nombre='Grupo B', codigo='GRB')
        self.usuario_a = CustomUser.objects.create_user(
            username='juan', password='clave123', grupo=self.grupo_a,
            first_name='Juan', last_name='Pérez', email='juan@example.com',
        )
        self.usuario_b = CustomUser.objects.create_user(
            username='ana', password='clave123', grupo=self.grupo_b, first_name='Ana',
        )

    def test_colegiado_unico_por_grupo(self):
        Medico.objects.create(grupo=self.grupo_a, usuario=self.usuario_a, colegiado='COL001')
        # mismo colegiado en otro grupo: permitido
        Medico.objects.create(grupo=self.grupo_b, usuario=self.usuario_b, colegiado='COL001')
        # mismo colegiado en el mismo grupo: falla
        otro_usuario = CustomUser.objects.create_user(
            username='otro', password='clave123', grupo=self.grupo_a,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Medico.objects.create(grupo=self.grupo_a, usuario=otro_usuario, colegiado='COL001')

    def test_usuario_solo_puede_tener_un_medico(self):
        Medico.objects.create(grupo=self.grupo_a, usuario=self.usuario_a, colegiado='COL001')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Medico.objects.create(grupo=self.grupo_a, usuario=self.usuario_a, colegiado='COL002')

    def test_soft_delete_no_borra_fila(self):
        medico = Medico.objects.create(grupo=self.grupo_a, usuario=self.usuario_a, colegiado='COL001')
        services.desactivar_medico(medico)
        medico.refresh_from_db()
        self.assertFalse(medico.is_active)
        self.assertTrue(Medico.objects.filter(pk=medico.pk).exists())

    def test_nombre_completo_y_email_delegan_en_usuario(self):
        medico = Medico.objects.create(grupo=self.grupo_a, usuario=self.usuario_a, colegiado='COL001')
        self.assertEqual(medico.nombre_completo, 'Juan Pérez')
        self.assertEqual(medico.email, 'juan@example.com')

    def test_str(self):
        medico = Medico.objects.create(grupo=self.grupo_a, usuario=self.usuario_a, colegiado='COL001')
        self.assertEqual(str(medico), 'Juan Pérez (COL001)')


class MedicoClinicaEspecialidadModelTests(TestCase):
    def setUp(self):
        self.grupo_a = Grupo.objects.create(nombre='Grupo A', codigo='GRA')
        self.usuario_a = CustomUser.objects.create_user(
            username='juan', password='clave123', grupo=self.grupo_a,
        )
        self.medico = Medico.objects.create(
            grupo=self.grupo_a, usuario=self.usuario_a, colegiado='COL001',
        )
        self.clinica = Clinica.objects.create(grupo=self.grupo_a, nombre='Aldaia', codigo='ALD')
        self.especialidad_1 = Especialidad.objects.create(nombre='Cardiología', profesion='Cardiólogo')
        self.especialidad_2 = Especialidad.objects.create(nombre='Pediatría', profesion='Pediatra')

    def test_medico_clinica_unico(self):
        MedicoClinicaEspecialidad.objects.create(
            medico=self.medico, clinica=self.clinica, especialidad=self.especialidad_1,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            MedicoClinicaEspecialidad.objects.create(
                medico=self.medico, clinica=self.clinica, especialidad=self.especialidad_2,
            )
