"""único punto de acceso al orm para Medico, MedicoClinicaEspecialidad y MedicoAusencia.

views.py, api/endpoints.py, serializers.py, filters.py y tables.py llaman
exclusivamente a estas funciones (excepción: admin.py, ver arquitectura.md §5).
"""

from django.shortcuts import get_object_or_404

from apps.medicos.exceptions import (
    AsignacionDuplicadaError,
    ClinicaFueraDeGrupoError,
    ColegiadoDuplicadoError,
    MedicosError,
    UsuarioFueraDeGrupoError,
    UsuarioYaEsMedicoError,
)
from apps.medicos.models import Medico, MedicoAusencia, MedicoClinicaEspecialidad
from apps.usuarios import services as usuarios_services

# --- Medico -------------------------------------------------------------


def listar_medicos(*, grupo=None, ids=None):
    """devuelve el queryset de médicos; filtra por grupo y/o por `ids` solo si se indican
    explícitamente (usado por el scoping de roles, ver `listar_medicos_visibles_para`).
    """
    qs = Medico.objects.select_related('grupo', 'usuario')
    if ids is not None:
        qs = qs.filter(pk__in=ids)
    return qs.for_grupo(grupo) if grupo is not None else qs.all()


def obtener_medico(medico_id, *, grupo=None, ids=None):
    """devuelve un médico por id (opcionalmente acotado a un grupo y/o a `ids`) o lanza 404."""
    return get_object_or_404(listar_medicos(grupo=grupo, ids=ids), pk=medico_id)


def obtener_medico_de_usuario(usuario):
    """devuelve el `Medico` asociado a un usuario o None si no tiene (útil para seeds/comandos)."""
    return Medico.objects.filter(usuario=usuario).first()


def listar_usuarios_disponibles(*, grupo=None, medico=None):
    """usuarios sin médico asociado aún, opcionalmente acotados a un grupo (para el select
    del formulario de alta: no ofrecer usuarios que ya son médicos).

    si se indica `medico` (edición), incluye también su propio usuario ya asignado, para
    que el formulario siga mostrando el valor actual aunque el campo esté deshabilitado.
    """
    qs = usuarios_services.listar_usuarios(grupo=grupo).filter(medico__isnull=True)
    if medico is not None:
        qs = qs | usuarios_services.listar_usuarios(grupo=grupo).filter(pk=medico.usuario_id)
    return qs


def crear_medico(*, grupo, usuario, colegiado, **datos):
    """crea un médico validando que `usuario` pertenezca al grupo, no tenga ya un médico
    asociado, y que `colegiado` no exista ya en ese grupo."""
    if usuario.grupo_id != grupo.id:
        raise UsuarioFueraDeGrupoError(
            f'el usuario "{usuario}" no pertenece al grupo "{grupo}".',
        )
    if Medico.objects.filter(usuario=usuario).exists():
        raise UsuarioYaEsMedicoError(f'el usuario "{usuario}" ya tiene un médico asociado.')
    if Medico.objects.filter(grupo=grupo, colegiado=colegiado).exists():
        raise ColegiadoDuplicadoError(
            f'ya existe un médico con colegiado "{colegiado}" en este grupo.',
        )
    return Medico.objects.create(grupo=grupo, usuario=usuario, colegiado=colegiado, **datos)


def actualizar_medico(medico, **datos):
    """actualiza los campos indicados de un médico, validando duplicados de colegiado.

    `usuario` no se reasigna desde aquí (el vínculo 1:1 se fija en `crear_medico`; la ui
    lo deshabilita en el formulario de edición, ver `MedicoForm`): si llega en `datos` se
    ignora en vez de arriesgar un `IntegrityError` de constraint único.
    """
    datos.pop('usuario', None)
    colegiado = datos.get('colegiado')
    if colegiado and Medico.objects.exclude(pk=medico.pk).filter(
        grupo=medico.grupo, colegiado=colegiado,
    ).exists():
        raise ColegiadoDuplicadoError(
            f'ya existe un médico con colegiado "{colegiado}" en este grupo.',
        )
    for campo, valor in datos.items():
        setattr(medico, campo, valor)
    medico.save()
    return medico


def desactivar_medico(medico):
    """soft delete: marca el médico como inactivo."""
    medico.is_active = False
    medico.save(update_fields=['is_active', 'updated_at'])
    return medico


def reactivar_medico(medico):
    """revierte el soft delete de un médico."""
    medico.is_active = True
    medico.save(update_fields=['is_active', 'updated_at'])
    return medico


def listar_medicos_visibles_para(usuario):
    """aplica el alcance por rol: superusuario ve todos los médicos; el resto ve los de su
    propio grupo — `Medico` pertenece al grupo, no a una clínica concreta (mismo criterio
    que `apps.pacientes.services.listar_pacientes_visibles_para`).
    """
    if usuario.is_superuser:
        return listar_medicos()
    return listar_medicos(grupo=usuario.grupo)


def obtener_medico_visible_para(medico_id, usuario):
    """devuelve un médico por id, acotado al alcance de `usuario`, o lanza 404.

    punto crítico de aislamiento por id directo: toda vista/viewset de detalle/edición de
    `Medico` debe resolver el objeto a través de esta función, nunca con
    `obtener_medico(pk)` a secas.
    """
    return get_object_or_404(listar_medicos_visibles_para(usuario), pk=medico_id)


# --- MedicoClinicaEspecialidad (especialidad por clínica) --------------------


def listar_asignaciones_clinica(*, medico=None):
    """devuelve el queryset de asignaciones médico-clínica-especialidad; filtra por médico
    si se indica."""
    qs = MedicoClinicaEspecialidad.objects.select_related('medico', 'clinica', 'especialidad')
    return qs.filter(medico=medico) if medico is not None else qs.all()


def obtener_asignacion_clinica(asignacion_id, *, medico=None):
    """devuelve una asignación por id (opcionalmente acotada a un médico) o lanza 404."""
    return get_object_or_404(listar_asignaciones_clinica(medico=medico), pk=asignacion_id)


def asignar_clinica_especialidad(*, medico, clinica, especialidad):
    """asigna a un médico una especialidad en una clínica.

    valida (ver arquitectura.md §4):
    - la clínica debe pertenecer al mismo grupo que el médico.
    - el médico no debe tener ya una asignación en esa clínica (una única especialidad por
      médico y clínica).
    """
    if clinica.grupo_id != medico.grupo_id:
        raise ClinicaFueraDeGrupoError(
            f'la clínica "{clinica}" no pertenece al grupo del médico "{medico}".',
        )
    if MedicoClinicaEspecialidad.objects.filter(medico=medico, clinica=clinica).exists():
        raise AsignacionDuplicadaError(
            f'el médico "{medico}" ya tiene una especialidad asignada en "{clinica}".',
        )
    return MedicoClinicaEspecialidad.objects.create(
        medico=medico, clinica=clinica, especialidad=especialidad,
    )


def quitar_asignacion_clinica(asignacion):
    """elimina una asignación médico-clínica-especialidad."""
    asignacion.delete()


# --- MedicoAusencia ---------------------------------------------------------


def listar_ausencias(*, medico=None, grupo=None):
    """devuelve el queryset de ausencias; filtra por médico y/o por grupo (a través de
    `medico__grupo`, ya que `MedicoAusencia` no tiene campo `grupo` directo).
    """
    qs = MedicoAusencia.objects.select_related('medico', 'medico__usuario')
    if medico is not None:
        qs = qs.filter(medico=medico)
    if grupo is not None:
        qs = qs.filter(medico__grupo=grupo)
    return qs


def listar_ausencias_visibles_para(usuario):
    """superusuario ve todas las ausencias; el resto ve las de su propio grupo."""
    if usuario.is_superuser:
        return listar_ausencias()
    return listar_ausencias(grupo=usuario.grupo)


def obtener_ausencia(ausencia_id, *, medico=None):
    """devuelve una ausencia por id (opcionalmente acotada a un médico) o lanza 404."""
    return get_object_or_404(listar_ausencias(medico=medico), pk=ausencia_id)


def obtener_ausencia_visible_para(ausencia_id, usuario):
    """devuelve una ausencia por id, acotada al alcance de `usuario`, o lanza 404."""
    return get_object_or_404(listar_ausencias_visibles_para(usuario), pk=ausencia_id)


def crear_ausencia(*, medico, fecha_inicio, fecha_fin, motivo, estado='P'):
    """crea una ausencia validando que las fechas sean coherentes."""
    if fecha_fin < fecha_inicio:
        raise MedicosError('la fecha de fin no puede ser anterior a la fecha de inicio.')
    return MedicoAusencia.objects.create(
        medico=medico, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
        motivo=motivo, estado=estado,
    )


def actualizar_ausencia(ausencia, **datos):
    """actualiza los campos indicados de una ausencia, validando coherencia de fechas."""
    fecha_inicio = datos.get('fecha_inicio', ausencia.fecha_inicio)
    fecha_fin = datos.get('fecha_fin', ausencia.fecha_fin)
    if fecha_fin < fecha_inicio:
        raise MedicosError('la fecha de fin no puede ser anterior a la fecha de inicio.')
    for campo, valor in datos.items():
        setattr(ausencia, campo, valor)
    ausencia.save()
    return ausencia


def desactivar_ausencia(ausencia):
    """soft delete: marca la ausencia como inactiva."""
    ausencia.is_active = False
    ausencia.save(update_fields=['is_active', 'updated_at'])
    return ausencia


def reactivar_ausencia(ausencia):
    """revierte el soft delete de una ausencia."""
    ausencia.is_active = True
    ausencia.save(update_fields=['is_active', 'updated_at'])
    return ausencia
