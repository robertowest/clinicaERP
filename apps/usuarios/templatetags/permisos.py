"""
filtros de plantilla para resolver permisos de rol sin repetir `is_staff` a mano en cada
template (ver apps.usuarios.permissions/apps.usuarios.mixins, mismo punto único de
autorización aplicado a las plantillas).
"""
from django import template

from apps.usuarios.services import usuario_tiene_permiso_generico

register = template.Library()


@register.filter(name='tiene_permiso_o_staff')
def tiene_permiso_o_staff(usuario, permiso):
    """
    True si `usuario` tiene `permiso` (catálogo granular); si no se indica `permiso` (apps
    aún no migradas al esquema de roles, como `usuarios`), cae a `is_staff` para no cambiar su
    comportamiento actual.
    """
    if not usuario or not usuario.is_authenticated:
        return False
    if permiso:
        return usuario_tiene_permiso_generico(usuario, permiso)
    return usuario.is_staff
