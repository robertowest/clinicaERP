from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _crear_catalogo_roles(sender, **kwargs):
    """recrea/actualiza el catálogo de roles y permisos tras cada `migrate` (igual
    mecanismo que usa `django.contrib.auth` para poblar `Permission` por modelo): así
    ampliar `apps.usuarios.roles.PERMISOS_POR_ROL` más adelante no exige una migración
    nueva, basta con volver a migrar.
    """
    from apps.usuarios.services import crear_catalogo_roles

    crear_catalogo_roles()


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.usuarios'
    verbose_name = 'Usuarios'

    def ready(self):
        post_migrate.connect(_crear_catalogo_roles, sender=self)
