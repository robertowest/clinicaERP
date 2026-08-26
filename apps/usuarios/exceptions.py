"""excepciones de dominio de apps.usuarios."""


class UsuariosError(Exception):
    """excepción base del dominio usuarios."""


class UsuarioDuplicadoError(UsuariosError):
    """ya existe un usuario con ese nombre de usuario."""


class ClinicaFueraDeGrupoError(UsuariosError):
    """la clínica indicada no pertenece al grupo del usuario (aislamiento multi-tenant)."""


class RolRequiereClinicaError(UsuariosError):
    """el rol indicado necesita una clínica concreta: no es un rol de alcance grupo/plataforma."""


class RolNoAceptaClinicaError(UsuariosError):
    """el rol indicado es de alcance grupo/plataforma: no admite una clínica concreta."""
