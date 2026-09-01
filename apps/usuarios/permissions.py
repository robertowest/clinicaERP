"""
permission classes drf reutilizables por cualquier app: resuelven el permiso granular del catálogo
`apps.usuarios.roles.PERMISOS_POR_ROL` contra `usuario_tiene_permiso_generico()`, nunca comparan rol/string
sueltos por su cuenta (arquitectura.md §6, punto único de autorización).
"""
from rest_framework import permissions

from apps.usuarios import services


def permiso_por_metodo(permiso_lectura, permiso_escritura):
    """
    fábrica de permission class: exige `permiso_lectura` en métodos seguros (GET/HEAD/OPTIONS) y `permiso_escritura`
    en el resto. usar cuando lectura y escritura de un recurso tienen permisos granulares distintos
    (p. ej. "clinics.view" / "clinics.manage").
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


def permiso_por_accion(*, ver, crear, actualizar, eliminar):
    """
    fábrica de permission class para catálogos con un permiso granular independiente por acción http
    (ver `apps.usuarios.roles.PERMISOS_POR_ROL`, ej. `patients.view/create/update/delete`), a diferencia del
    esquema view/manage de `permiso_por_metodo()`.
    """
    permiso_por_verbo = {
        'GET': ver,
        'HEAD': ver,
        'OPTIONS': ver,
        'POST': crear,
        'PUT': actualizar,
        'PATCH': actualizar,
        'DELETE': eliminar,
    }

    class _PermisoPorAccion(permissions.BasePermission):
        def has_permission(self, request, view):
            if not (request.user and request.user.is_authenticated):
                return False
            permiso = permiso_por_verbo.get(request.method)
            return permiso is not None and services.usuario_tiene_permiso_generico(
                request.user, permiso,
            )

    return _PermisoPorAccion
