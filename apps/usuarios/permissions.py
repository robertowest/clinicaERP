"""permission classes drf reutilizables por cualquier app: resuelven el permiso granular
del catálogo `apps.usuarios.roles.PERMISOS_POR_ROL` contra `usuario_tiene_permiso_generico()`,
nunca comparan rol/string sueltos por su cuenta (arquitectura.md §6, punto único de autorización).
"""
from rest_framework import permissions

from apps.usuarios import services


def permiso_por_metodo(permiso_lectura, permiso_escritura):
    """fábrica de permission class: exige `permiso_lectura` en métodos seguros (GET/HEAD/
    OPTIONS) y `permiso_escritura` en el resto. usar cuando lectura y escritura de un recurso
    tienen permisos granulares distintos (p. ej. "clinics.view" / "clinics.manage").
    """

    class _PermisoPorMetodo(permissions.BasePermission):
        def has_permission(self, request, view):
            if not (request.user and request.user.is_authenticated):
                return False
            permiso = (
                permiso_lectura if request.method in permissions.SAFE_METHODS else permiso_escritura
            )
            return services.usuario_tiene_permiso_generico(request.user, permiso)

    return _PermisoPorMetodo
