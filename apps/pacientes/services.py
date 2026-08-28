"""único punto de acceso al orm para Paciente.

views.py, api/endpoints.py, serializers.py, filters.py y tables.py llaman
exclusivamente a estas funciones (excepción: admin.py, ver arquitectura.md §5).
"""

from django.shortcuts import get_object_or_404

from apps.pacientes.exceptions import DocumentoDuplicadoError, NhcDuplicadoError
from apps.pacientes.models import Paciente

# --- Paciente -------------------------------------------------------------


def listar_pacientes(*, grupo=None, ids=None):
    """devuelve el queryset de pacientes; filtra por grupo y/o por `ids` solo si se indican
    explícitamente (usado por el scoping de roles, ver `listar_pacientes_visibles_para`).
    """
    qs = Paciente.objects.select_related('grupo')
    if ids is not None:
        qs = qs.filter(pk__in=ids)
    return qs.for_grupo(grupo) if grupo is not None else qs.all()


def obtener_paciente(paciente_id, *, grupo=None, ids=None):
    """devuelve un paciente por id (opcionalmente acotado a un grupo y/o a `ids`) o lanza 404."""
    return get_object_or_404(listar_pacientes(grupo=grupo, ids=ids), pk=paciente_id)


def crear_paciente(*, grupo, nhc, documento_tipo, documento_numero, **datos):
    """crea un paciente validando que `nhc` y `documento_tipo`+`documento_numero` no existan
    ya en ese grupo (evita duplicar la ficha del mismo paciente)."""
    if Paciente.objects.filter(grupo=grupo, nhc=nhc).exists():
        raise NhcDuplicadoError(f'ya existe un paciente con nhc "{nhc}" en este grupo.')
    if Paciente.objects.filter(
        grupo=grupo, documento_tipo=documento_tipo, documento_numero=documento_numero,
    ).exists():
        raise DocumentoDuplicadoError('ya existe un paciente con ese documento en este grupo.')
    return Paciente.objects.create(
        grupo=grupo, nhc=nhc, documento_tipo=documento_tipo,
        documento_numero=documento_numero, **datos,
    )


def actualizar_paciente(paciente, **datos):
    """actualiza los campos indicados de un paciente, validando duplicados de nhc/documento."""
    nhc = datos.get('nhc')
    if nhc and Paciente.objects.exclude(pk=paciente.pk).filter(
        grupo=paciente.grupo, nhc=nhc,
    ).exists():
        raise NhcDuplicadoError(f'ya existe un paciente con nhc "{nhc}" en este grupo.')
    if 'documento_tipo' in datos or 'documento_numero' in datos:
        tipo = datos.get('documento_tipo', paciente.documento_tipo)
        numero = datos.get('documento_numero', paciente.documento_numero)
        duplicado = Paciente.objects.exclude(pk=paciente.pk).filter(
            grupo=paciente.grupo, documento_tipo=tipo, documento_numero=numero,
        )
        if duplicado.exists():
            raise DocumentoDuplicadoError('ya existe un paciente con ese documento en este grupo.')
    for campo, valor in datos.items():
        setattr(paciente, campo, valor)
    paciente.save()
    return paciente


def desactivar_paciente(paciente):
    """soft delete: marca el paciente como inactivo."""
    paciente.is_active = False
    paciente.save(update_fields=['is_active', 'updated_at'])
    return paciente


def reactivar_paciente(paciente):
    """revierte el soft delete de un paciente."""
    paciente.is_active = True
    paciente.save(update_fields=['is_active', 'updated_at'])
    return paciente


def listar_pacientes_visibles_para(usuario):
    """aplica el alcance por rol: superusuario ve todos los pacientes; el resto (cualquier
    rol con patients.*) ve los de su propio grupo — `Paciente` pertenece al grupo, no a una
    clínica concreta, así que no hace falta más granularidad que la de `organizacion` para
    `Clinica` (ver `apps.organizacion.services.listar_clinicas_visibles_para`).
    """
    if usuario.is_superuser:
        return listar_pacientes()
    return listar_pacientes(grupo=usuario.grupo)


def obtener_paciente_visible_para(paciente_id, usuario):
    """devuelve un paciente por id, acotado al alcance de `usuario`, o lanza 404.

    punto crítico de aislamiento por id directo: toda vista/viewset de detalle/edición de
    `Paciente` debe resolver el objeto a través de esta función, nunca con
    `obtener_paciente(pk)` a secas.
    """
    return get_object_or_404(listar_pacientes_visibles_para(usuario), pk=paciente_id)
