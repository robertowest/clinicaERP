"""mixins de autorización basados en roles/permisos, para las vistas html de cualquier app
(equivalente a `apps.usuarios.permissions` para la api).
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from apps.usuarios import services


class PermisoRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """restringe una vista a usuarios autenticados que tengan `permiso_requerido` en alguna
    de sus asignaciones de rol (o sean superusuario).

    sustituye a `apps.core.mixins.StaffRequiredMixin` allí donde ya existe un permiso granular
    definido en `apps.usuarios.roles.PERMISOS_POR_ROL`. no hace falta `raise_exception`:
    `AccessMixin.handle_no_permission` ya distingue anónimo (redirige a login) de
    autenticado-sin-permiso (403).
    """

    permiso_requerido = None

    def test_func(self):
        return services.usuario_tiene_permiso_generico(self.request.user, self.permiso_requerido)
