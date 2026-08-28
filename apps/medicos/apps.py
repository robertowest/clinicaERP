from django.apps import AppConfig


class MedicosConfig(AppConfig):
    """configuración de la app medicos (Medico, MedicoClinicaEspecialidad)."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.medicos'
    verbose_name = 'Médicos'

    def ready(self):
        from apps.medicos import signals  # noqa: F401
