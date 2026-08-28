"""registra el viewset de pacientes en el router raíz de la api."""
from apps.pacientes.api.endpoints import PacienteViewSet


def register(router):
    router.register('pacientes', PacienteViewSet, basename='paciente')
