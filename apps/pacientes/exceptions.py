"""excepciones de dominio de apps.pacientes."""


class PacientesError(Exception):
    """excepción base del dominio pacientes."""


class NhcDuplicadoError(PacientesError):
    """nhc ya existente para ese grupo."""


class DocumentoDuplicadoError(PacientesError):
    """documento_tipo+documento_numero ya existente para ese grupo."""
