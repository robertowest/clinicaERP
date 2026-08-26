from django.apps import AppConfig


class OrganizacionConfig(AppConfig):
    """configuración de la app organizacion (grupo, clinica, especialidad)."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.organizacion'
    verbose_name = 'Organización'

    def ready(self):
        from apps.organizacion import signals  # noqa: F401
