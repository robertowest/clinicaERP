"""managers reutilizables para el aislamiento multi-tenant.

no filtran por grupo de forma implícita: cada app decide explícitamente cuándo
llamar a `for_grupo()` desde su `services.py`, para no romper el django admin
(que necesita poder ver registros de todos los grupos).
"""
from django.db import models


class TenantQuerySet(models.QuerySet):
    """queryset que expone el filtrado explícito por grupo."""

    def for_grupo(self, grupo):
        """devuelve únicamente los registros pertenecientes al grupo indicado."""
        return self.filter(grupo=grupo)


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    """manager por defecto de los modelos `GroupOwnedModel`."""
