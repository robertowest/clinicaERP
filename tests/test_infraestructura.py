"""smoke test de infraestructura (fase 7): comprueba que el entregable descrito en
prompt.md §37 está realmente accesible — admin, api raíz con los recursos esperados y
documentación openapi (drf-spectacular) — sin repetir la lógica de negocio, ya cubierta
por los tests de cada app.
"""
from rest_framework.test import APITestCase

from apps.usuarios.models import CustomUser

RECURSOS_ESPERADOS = {
    'grupos', 'clinicas', 'especialidades', 'usuarios', 'pacientes', 'medicos',
    'ausencias',
}


class InfraestructuraTests(APITestCase):
    def setUp(self):
        self.superadmin = CustomUser.objects.create_user(
            username='root', password='clave123', is_superuser=True, is_staff=True,
        )

    def test_admin_accesible_para_superusuario(self):
        self.client.force_login(self.superadmin)
        respuesta = self.client.get('/admin/')
        self.assertEqual(respuesta.status_code, 200)

    def test_api_v1_expone_los_recursos_principales(self):
        self.client.force_authenticate(self.superadmin)
        respuesta = self.client.get('/api/v1/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(RECURSOS_ESPERADOS, set(respuesta.data.keys()))

    def test_openapi_docs_accesibles_sin_autenticacion(self):
        # SPECTACULAR_SETTINGS.SERVE_PERMISSIONS es AllowAny por defecto: la documentación
        # debe poder consultarse sin login, aunque los propios endpoints sí lo exijan.
        for url in ('/api/schema/', '/api/docs/', '/api/redoc/'):
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 200, url)
