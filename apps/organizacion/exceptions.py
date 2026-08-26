"""excepciones de dominio de apps.organizacion."""


class OrganizacionError(Exception):
    """excepción base del dominio organizacion."""


class CodigoDuplicadoError(OrganizacionError):
    """código ya existente en su ámbito (global para Grupo/Especialidad, por grupo para Clinica)."""
