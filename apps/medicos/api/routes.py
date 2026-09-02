"""registra los viewsets de medicos y ausencias en el router raíz de la api."""
from apps.medicos.api.endpoints import MedicoAusenciaViewSet, MedicoViewSet


def register(router):
    router.register('medicos', MedicoViewSet, basename='medico')
    router.register('ausencias', MedicoAusenciaViewSet, basename='ausencia')
