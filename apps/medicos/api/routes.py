"""registra el viewset de medicos en el router raíz de la api."""
from apps.medicos.api.endpoints import MedicoViewSet


def register(router):
    router.register('medicos', MedicoViewSet, basename='medico')
