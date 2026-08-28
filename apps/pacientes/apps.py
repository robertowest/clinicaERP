from django.apps import AppConfig


class PacientesConfig(AppConfig):
    """configuración de la app pacientes (Paciente)."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pacientes'
    verbose_name = 'Pacientes'

    def ready(self):
        from apps.pacientes import signals  # noqa: F401
