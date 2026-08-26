"""registra los viewsets de usuarios en el router raíz de la api."""
from apps.usuarios.api.endpoints import UsuarioViewSet


def register(router):
    router.register('usuarios', UsuarioViewSet, basename='usuario-api')
