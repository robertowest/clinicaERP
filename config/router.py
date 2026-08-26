"""router raíz de la api: cada app registra aquí su viewset a medida que se implementa."""
from rest_framework.routers import DefaultRouter

from apps.organizacion.api.routes import register as register_organizacion
from apps.usuarios.api.routes import register as register_usuarios

router = DefaultRouter()

register_organizacion(router)
register_usuarios(router)
