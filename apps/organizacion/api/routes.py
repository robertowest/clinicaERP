"""registra los viewsets de organizacion en el router raíz de la api."""
from apps.organizacion.api.endpoints import ClinicaViewSet, EspecialidadViewSet, GrupoViewSet


def register(router):
    router.register('grupos', GrupoViewSet, basename='grupo')
    router.register('clinicas', ClinicaViewSet, basename='clinica')
    router.register('especialidades', EspecialidadViewSet, basename='especialidad')
