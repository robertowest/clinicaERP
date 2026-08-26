"""único punto de acceso al orm para Grupo, Clinica y Especialidad.

views.py, api/endpoints.py, serializers.py, filters.py y tables.py llaman
exclusivamente a estas funciones (excepción: admin.py, ver arquitectura.md §5).
"""

from django.shortcuts import get_object_or_404

from apps.organizacion.exceptions import CodigoDuplicadoError
from apps.organizacion.models import Clinica, Especialidad, Grupo

# --- Grupo -------------------------------------------------------------


def listar_grupos():
    """devuelve el queryset de todos los grupos (activos e inactivos)."""
    return Grupo.objects.all()


def obtener_grupo(grupo_id):
    """devuelve un grupo por id o lanza 404."""
    return get_object_or_404(Grupo, pk=grupo_id)


def obtener_grupo_por_codigo(codigo):
    """devuelve un grupo por código o None si no existe (útil para seeds/comandos)."""
    return Grupo.objects.filter(codigo=codigo).first()


def crear_grupo(*, nombre, codigo, **extra):
    """crea un grupo validando que el código no exista ya."""
    if Grupo.objects.filter(codigo=codigo).exists():
        raise CodigoDuplicadoError(f'ya existe un grupo con código "{codigo}".')
    return Grupo.objects.create(nombre=nombre, codigo=codigo, **extra)


def actualizar_grupo(grupo, **datos):
    """actualiza los campos indicados de un grupo, validando duplicados de código."""
    codigo = datos.get('codigo')
    if codigo and Grupo.objects.exclude(pk=grupo.pk).filter(codigo=codigo).exists():
        raise CodigoDuplicadoError(f'ya existe un grupo con código "{codigo}".')
    for campo, valor in datos.items():
        setattr(grupo, campo, valor)
    grupo.save()
    return grupo


def desactivar_grupo(grupo):
    """soft delete: marca el grupo como inactivo."""
    grupo.is_active = False
    grupo.save(update_fields=['is_active', 'updated_at'])
    return grupo


def reactivar_grupo(grupo):
    """revierte el soft delete de un grupo."""
    grupo.is_active = True
    grupo.save(update_fields=['is_active', 'updated_at'])
    return grupo


# --- Clinica -------------------------------------------------------------


def listar_clinicas(*, grupo=None):
    """devuelve el queryset de clínicas; filtra por grupo solo si se indica explícitamente."""
    qs = Clinica.objects.select_related('grupo').prefetch_related('especialidades')
    return qs.for_grupo(grupo) if grupo is not None else qs.all()


def obtener_clinica(clinica_id, *, grupo=None):
    """devuelve una clínica por id (opcionalmente acotada a un grupo) o lanza 404."""
    qs = Clinica.objects.for_grupo(grupo) if grupo is not None else Clinica.objects.all()
    return get_object_or_404(qs, pk=clinica_id)


def obtener_clinica_por_codigo(grupo, codigo):
    """devuelve la clínica de un grupo por código o None si no existe (útil para seeds/comandos)."""
    return Clinica.objects.filter(grupo=grupo, codigo=codigo).first()


def crear_clinica(*, grupo, nombre, codigo, especialidades=None, **extra):
    """crea una clínica validando que el código no exista ya dentro del grupo."""
    if Clinica.objects.filter(grupo=grupo, codigo=codigo).exists():
        raise CodigoDuplicadoError(f'ya existe una clínica con código "{codigo}" en este grupo.')
    clinica = Clinica.objects.create(grupo=grupo, nombre=nombre, codigo=codigo, **extra)
    if especialidades is not None:
        clinica.especialidades.set(especialidades)
    return clinica


def actualizar_clinica(clinica, *, especialidades=None, **datos):
    """actualiza los campos indicados de una clínica, validando duplicados de código."""
    codigo = datos.get('codigo')
    duplicado = Clinica.objects.exclude(pk=clinica.pk).filter(grupo=clinica.grupo, codigo=codigo)
    if codigo and duplicado.exists():
        raise CodigoDuplicadoError(f'ya existe una clínica con código "{codigo}" en este grupo.')
    for campo, valor in datos.items():
        setattr(clinica, campo, valor)
    clinica.save()
    if especialidades is not None:
        clinica.especialidades.set(especialidades)
    return clinica


def desactivar_clinica(clinica):
    """soft delete: marca la clínica como inactiva."""
    clinica.is_active = False
    clinica.save(update_fields=['is_active', 'updated_at'])
    return clinica


def reactivar_clinica(clinica):
    """revierte el soft delete de una clínica."""
    clinica.is_active = True
    clinica.save(update_fields=['is_active', 'updated_at'])
    return clinica


# --- Especialidad -------------------------------------------------------------


def listar_especialidades():
    """devuelve el queryset de todas las especialidades (activas e inactivas)."""
    return Especialidad.objects.all()


def obtener_especialidad(especialidad_id):
    """devuelve una especialidad por id o lanza 404."""
    return get_object_or_404(Especialidad, pk=especialidad_id)


def obtener_especialidad_por_nombre(nombre):
    """devuelve una especialidad por nombre o None si no existe (útil para seeds/comandos)."""
    return Especialidad.objects.filter(nombre=nombre).first()


def crear_especialidad(*, nombre, profesion=None, **extra):
    """crea una especialidad validando que el nombre no exista ya."""
    if Especialidad.objects.filter(nombre=nombre).exists():
        raise CodigoDuplicadoError(f'ya existe una especialidad con nombre "{nombre}".')
    return Especialidad.objects.create(nombre=nombre, profesion=profesion, **extra)


def actualizar_especialidad(especialidad, **datos):
    """actualiza los campos indicados de una especialidad."""
    for campo, valor in datos.items():
        setattr(especialidad, campo, valor)
    especialidad.save()
    return especialidad


def desactivar_especialidad(especialidad):
    """soft delete: marca la especialidad como inactiva."""
    especialidad.is_active = False
    especialidad.save(update_fields=['is_active', 'updated_at'])
    return especialidad


def reactivar_especialidad(especialidad):
    """revierte el soft delete de una especialidad."""
    especialidad.is_active = True
    especialidad.save(update_fields=['is_active', 'updated_at'])
    return especialidad


def asignar_especialidad_a_clinica(clinica, especialidad):
    """añade una especialidad al catálogo que ofrece una clínica."""
    clinica.especialidades.add(especialidad)
    return clinica


def quitar_especialidad_de_clinica(clinica, especialidad):
    """quita una especialidad del catálogo que ofrece una clínica."""
    clinica.especialidades.remove(especialidad)
    return clinica
