"""modelos abstractos reutilizables por el resto de apps."""
from django.db import models

from apps.core.managers import TenantManager


class BaseModel(models.Model):
    """añade auditoría mínima y soporte de soft delete a los modelos que lo heredan."""

    is_active = models.BooleanField('activo', default=True)
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('fecha de actualización', auto_now=True)

    class Meta:
        abstract = True


class GroupOwnedModel(BaseModel):
    """modelo abstracto para entidades que pertenecen al ámbito de un grupo (multi-tenant).

    el manager por defecto no filtra por grupo: el filtrado se aplica explícitamente
    desde `services.py` mediante `for_grupo()`, nunca de forma implícita en las vistas.
    """

    grupo = models.ForeignKey(
        'organizacion.Grupo',
        verbose_name='grupo',
        on_delete=models.PROTECT,
        related_name='%(class)ss',
    )

    objects = TenantManager()

    class Meta:
        abstract = True
