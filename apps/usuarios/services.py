"""único punto de acceso al orm para CustomUser y UsuarioClinica.

views.py, api/endpoints.py, serializers.py, filters.py y tables.py llaman
exclusivamente a estas funciones (excepción: admin.py, ver arquitectura.md §5).
"""

from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.organizacion.models import Clinica
from apps.usuarios.exceptions import (
    ClinicaFueraDeGrupoError,
    RolNoAceptaClinicaError,
    RolRequiereClinicaError,
    UsuarioDuplicadoError,
)
from apps.usuarios.models import CustomUser, UsuarioClinica
from apps.usuarios.roles import ROLES_SIN_CLINICA, rol_tiene_permiso

# --- CustomUser -------------------------------------------------------------


def listar_usuarios(*, grupo=None):
    """devuelve el queryset de todos los usuarios; filtra por grupo solo si se indica."""
    qs = CustomUser.objects.select_related('grupo')
    return qs.filter(grupo=grupo) if grupo is not None else qs.all()


def obtener_usuario(usuario_id, *, grupo=None):
    """devuelve un usuario por id (opcionalmente acotado a un grupo) o lanza 404."""
    qs = CustomUser.objects.filter(grupo=grupo) if grupo is not None else CustomUser.objects.all()
    return get_object_or_404(qs, pk=usuario_id)


def crear_usuario(
    *, username, password, email='', grupo=None, first_name='', last_name='',
    is_staff=False, **extra,
):
    """crea un usuario validando que el nombre de usuario no exista ya.

    valida la contraseña con los validadores configurados en `AUTH_PASSWORD_VALIDATORS`
    antes de guardarla (el `ModelForm`/serializer no aplican estos validadores por sí solos).
    """
    if CustomUser.objects.filter(username=username).exists():
        raise UsuarioDuplicadoError(f'ya existe un usuario con nombre de usuario "{username}".')
    validate_password(password)
    return CustomUser.objects.create_user(
        username=username, email=email, grupo=grupo, first_name=first_name,
        last_name=last_name, is_staff=is_staff, password=password, **extra,
    )


def actualizar_usuario(usuario, **datos):
    """actualiza los campos indicados de un usuario, validando duplicados de username.

    nunca recibe `password` aquí: usar `cambiar_password()` explícitamente.
    """
    username = datos.get('username')
    if username and CustomUser.objects.exclude(pk=usuario.pk).filter(username=username).exists():
        raise UsuarioDuplicadoError(f'ya existe un usuario con nombre de usuario "{username}".')
    for campo, valor in datos.items():
        setattr(usuario, campo, valor)
    usuario.save()
    return usuario


def cambiar_password(usuario, password):
    """valida y cambia la contraseña de un usuario."""
    validate_password(password, user=usuario)
    usuario.set_password(password)
    usuario.save(update_fields=['password'])
    return usuario


def desactivar_usuario(usuario):
    """soft delete: marca el usuario como inactivo (le impide iniciar sesión)."""
    usuario.is_active = False
    usuario.save(update_fields=['is_active'])
    return usuario


def reactivar_usuario(usuario):
    """revierte el soft delete de un usuario."""
    usuario.is_active = True
    usuario.save(update_fields=['is_active'])
    return usuario


# --- UsuarioClinica (rol por clínica) ----------------------------------------


def listar_asignaciones(*, usuario=None):
    """devuelve el queryset de asignaciones usuario-clínica; filtra por usuario si se indica."""
    qs = UsuarioClinica.objects.select_related('usuario', 'clinica')
    return qs.filter(usuario=usuario) if usuario is not None else qs.all()


def obtener_asignacion(asignacion_id, *, usuario=None):
    """devuelve una asignación por id (opcionalmente acotada a un usuario) o lanza 404."""
    qs = listar_asignaciones(usuario=usuario)
    return get_object_or_404(qs, pk=asignacion_id)


def asignar_rol(*, usuario, rol, clinica=None):
    """asigna un rol a un usuario, opcionalmente ligado a una clínica.

    valida (ver arquitectura.md §4):
    - roles de alcance grupo/plataforma (`SUPERADMIN`, `GROUP_ADMIN`) no aceptan clínica.
    - el resto de roles requieren una clínica.
    - la clínica debe pertenecer al mismo grupo que el usuario.
    """
    if rol in ROLES_SIN_CLINICA:
        if clinica is not None:
            raise RolNoAceptaClinicaError(
                f'el rol "{rol}" es de alcance grupo/plataforma y no admite clínica.',
            )
    else:
        if clinica is None:
            raise RolRequiereClinicaError(f'el rol "{rol}" requiere indicar una clínica.')
        if clinica.grupo_id != usuario.grupo_id:
            raise ClinicaFueraDeGrupoError(
                f'la clínica "{clinica}" no pertenece al grupo del usuario "{usuario}".',
            )
    return UsuarioClinica.objects.create(usuario=usuario, clinica=clinica, rol=rol)


def quitar_asignacion(asignacion):
    """elimina una asignación de rol usuario-clínica."""
    asignacion.delete()


def listar_clinicas_de_usuario(usuario, *, rol=None):
    """devuelve el queryset de clínicas en las que el usuario tiene un rol asignado.

    si se indica `rol`, acota a las asignaciones con ese rol concreto (por ejemplo, para
    resolver el alcance de un `CLINIC_ADMIN`: solo las clínicas donde tiene ese rol, no
    todas las que pudiera tener asignadas con otro rol).
    """
    qs = Clinica.objects.filter(usuarios_asignados__usuario=usuario)
    if rol is not None:
        qs = qs.filter(usuarios_asignados__rol=rol)
    return qs.distinct()


def listar_roles_de_usuario(usuario):
    """devuelve los roles (strings) que tiene asignados un usuario, sin duplicados."""
    return list(
        UsuarioClinica.objects.filter(usuario=usuario).values_list('rol', flat=True).distinct(),
    )


def obtener_datos_me(usuario):
    """arma el payload de `GET /api/v1/auth/me/` (prompt.md §13): usuario + grupo +
    clínicas accesibles (con su rol) + roles.

    un rol de alcance grupo/plataforma (`clinica=None`) da acceso a todas las clínicas
    activas del grupo del usuario con ese mismo rol; el resto de asignaciones aportan
    su clínica concreta tal cual.
    """
    asignaciones = list(listar_asignaciones(usuario=usuario))
    clinics = []
    for asignacion in asignaciones:
        if asignacion.clinica is not None:
            clinicas = [asignacion.clinica]
        elif usuario.grupo_id is not None:
            clinicas = list(Clinica.objects.filter(grupo=usuario.grupo, is_active=True))
        else:
            clinicas = []
        clinics.extend(
            {'id': c.id, 'nombre': c.nombre, 'codigo': c.codigo, 'rol': asignacion.rol}
            for c in clinicas
        )

    return {
        'id': usuario.id,
        'username': usuario.username,
        'email': usuario.email,
        'first_name': usuario.first_name,
        'last_name': usuario.last_name,
        'is_staff': usuario.is_staff,
        'group': (
            {'id': usuario.grupo_id, 'nombre': usuario.grupo.nombre, 'codigo': usuario.grupo.codigo}
            if usuario.grupo_id else None
        ),
        'clinics': clinics,
        'roles': [a.rol for a in asignaciones],
    }


def usuario_tiene_permiso(usuario, clinica, permiso):
    """punto único de autorización (arquitectura.md §6, problema 2): tanto la ui html
    como la api deben resolver permisos llamando a esta función, nunca reimplementando
    la regla por su cuenta.

    comprueba los roles del usuario en `clinica` (o de alcance grupo/plataforma, que
    aplican a cualquier clínica del mismo grupo) y si alguno concede `permiso`.
    """
    if usuario.is_superuser:
        return True
    # la asignación aplica si es para esa clínica exacta o si es un rol de alcance
    # grupo/plataforma (`clinica=None`), que cubre cualquier clínica del grupo.
    roles = UsuarioClinica.objects.filter(usuario=usuario).filter(
        Q(clinica=clinica) | Q(clinica__isnull=True),
    ).values_list('rol', flat=True)
    return any(rol_tiene_permiso(rol, permiso) for rol in roles)


def usuario_tiene_permiso_generico(usuario, permiso):
    """comprueba si `usuario` tiene, en cualquiera de sus asignaciones (cualquier clínica o
    de alcance grupal), un rol que conceda `permiso`.

    usar cuando no hay una clínica concreta sobre la que resolver (listados/altas de recursos
    de alcance grupo, como grupo/clínica/especialidad); para permisos ligados a una clínica en
    concreto seguir usando `usuario_tiene_permiso()`.
    """
    if usuario.is_superuser:
        return True
    roles = UsuarioClinica.objects.filter(usuario=usuario).values_list('rol', flat=True)
    return any(rol_tiene_permiso(rol, permiso) for rol in roles)
