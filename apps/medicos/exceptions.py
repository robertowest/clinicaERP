"""excepciones de dominio de apps.medicos."""


class MedicosError(Exception):
    """excepción base del dominio medicos."""


class ColegiadoDuplicadoError(MedicosError):
    """n.º de colegiado ya existente para ese grupo."""


class UsuarioYaEsMedicoError(MedicosError):
    """el usuario indicado ya tiene un `Medico` asociado (relación 1:1)."""


class UsuarioFueraDeGrupoError(MedicosError):
    """el usuario indicado no pertenece al grupo del médico."""


class ClinicaFueraDeGrupoError(MedicosError):
    """la clínica indicada no pertenece al grupo del médico."""


class AsignacionDuplicadaError(MedicosError):
    """el médico ya tiene una especialidad asignada en esa clínica."""
