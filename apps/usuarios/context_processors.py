"""context processors de la app usuarios: exponen a las plantillas los roles y permisos
del usuario autenticado resueltos contra nuestro esquema multitenant (`UsuarioClinica` →
`Rol` → `auth_group_permissions`), en lugar de las relaciones nativas de django
(`user.groups.all`, `user.user_permissions.all`, `perms.<app>`) que este sistema ya no
usa.

expone dos variables:
- `roles`: códigos estables de rol (`RolPerfil.codigo`) del usuario, sin duplicados.
- `perms`: mapa `{codename: True}` de todos los permisos concedidos por sus roles, para
  poder usar `{% if perms.patients.view %}` en las plantillas.
"""
from apps.usuarios.services import codigos_permisos_de_usuario, listar_roles_de_usuario


def usuario_context(request):
    """devuelve los roles y permisos del usuario de la petición (vacío si no autenticado)."""
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        roles = listar_roles_de_usuario(user)
        perms = {codename: True for codename in codigos_permisos_de_usuario(user)}
    else:
        roles = []
        perms = {}
    return {'roles': roles, 'perms': perms}
