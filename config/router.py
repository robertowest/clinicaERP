"""router raíz de la api: cada app registra aquí su viewset a medida que se implementa."""
from rest_framework.routers import DefaultRouter

from apps.medicos.api.routes import register as register_medicos
from apps.organizacion.api.routes import register as register_organizacion
from apps.pacientes.api.routes import register as register_pacientes
from apps.programacion.api.routes import register as register_programacion
from apps.usuarios.api.routes import register as register_usuarios

router = DefaultRouter()

register_organizacion(router)
register_usuarios(router)
register_pacientes(router)
register_medicos(router)
register_programacion(router)
