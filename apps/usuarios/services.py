"""
único punto de acceso al orm para CustomUser y UsuarioClinica.

views.py, api/endpoints.py, serializers.py, filters.py y tables.py llaman
exclusivamente a estas funciones (excepción: admin.py, ver arquitectura.md §5).
"""

from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from django.contrib.contenttypes.models import ContentType
from django.db import OperationalError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import NoReverseMatch, reverse

from apps.organizacion.models import Clinica
from apps.usuarios.exceptions import (
    ClinicaFueraDeGrupoError,
    RolNoAceptaClinicaError,
    RolRequiereClinicaError,
    UsuarioDuplicadoError,
)
from apps.usuarios.models import CustomUser, PermisoPersonalizado, Rol, RolPerfil, UsuarioClinica
from apps.usuarios.roles import (
    CATALOGO_PERMISOS, PERMISOS_POR_ROL, PRIORIDAD_ROLES_LOGIN, ROLES_INICIALES,
)

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
    """
    crea un usuario validando que el nombre de usuario no exista ya.
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
    """
    actualiza los campos indicados de un usuario, validando duplicados de username.
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
    qs = UsuarioClinica.objects.select_related('usuario', 'clinica', 'rol', 'rol__perfil')
    return qs.filter(usuario=usuario) if usuario is not None else qs.all()


def obtener_asignacion(asignacion_id, *, usuario=None):
    """devuelve una asignación por id (opcionalmente acotada a un usuario) o lanza 404."""
    qs = listar_asignaciones(usuario=usuario)
    return get_object_or_404(qs, pk=asignacion_id)


def listar_roles():
    """devuelve el queryset de roles disponibles para asignar (selects de formularios/api)."""
    return Rol.objects.select_related('perfil').order_by('name')


def obtener_rol_por_codigo(codigo):
    """devuelve un `Rol` por su código estable (`RolPerfil.codigo`, ver `roles.Roles`)."""
    return Rol.objects.select_related('perfil').get(perfil__codigo=codigo)


def _resolver_rol(rol):
    """acepta un `Rol` ya resuelto o su código estable y siempre devuelve la instancia."""
    return rol if isinstance(rol, Rol) else obtener_rol_por_codigo(rol)


def asignar_rol(*, usuario, rol, clinica=None):
    """
    asigna un rol a un usuario, opcionalmente ligado a una clínica.

    `rol` acepta tanto una instancia de `Rol` como su código estable (`RolPerfil.codigo`).

    valida (ver arquitectura.md §4):
    - los roles de alcance grupo/plataforma (`RolPerfil.requiere_clinica=False`) no
      aceptan clínica.
    - el resto de roles requieren una clínica.
    - la clínica debe pertenecer al mismo grupo que el usuario.
    """
    rol_obj = _resolver_rol(rol)
    if not rol_obj.perfil.requiere_clinica:
        if clinica is not None:
            raise RolNoAceptaClinicaError(
                f'el rol "{rol_obj}" es de alcance grupo/plataforma y no admite clínica.',
            )
    else:
        if clinica is None:
            raise RolRequiereClinicaError(f'el rol "{rol_obj}" requiere indicar una clínica.')
        if clinica.grupo_id != usuario.grupo_id:
            raise ClinicaFueraDeGrupoError(
                f'la clínica "{clinica}" no pertenece al grupo del usuario "{usuario}".',
            )
    return UsuarioClinica.objects.create(usuario=usuario, clinica=clinica, rol=rol_obj)


def quitar_asignacion(asignacion):
    """elimina una asignación de rol usuario-clínica."""
    asignacion.delete()


def listar_clinicas_de_usuario(usuario, *, rol=None):
    """
    devuelve el queryset de clínicas en las que el usuario tiene un rol asignado.

    si se indica `rol` (instancia o código), acota a las asignaciones con ese rol
    concreto (por ejemplo, para resolver el alcance de un `CLINIC_ADMIN`: solo las
    clínicas donde tiene ese rol, no todas las que pudiera tener asignadas con otro rol).
    """
    qs = Clinica.objects.filter(usuarios_asignados__usuario=usuario)
    if rol is not None:
        qs = qs.filter(usuarios_asignados__rol=_resolver_rol(rol))
    return qs.distinct()


def listar_roles_de_usuario(usuario):
    """devuelve los códigos de rol (`RolPerfil.codigo`) que tiene asignados un usuario,
    sin duplicados."""
    return list(
        UsuarioClinica.objects.filter(usuario=usuario)
        .values_list('rol__perfil__codigo', flat=True).distinct(),
    )


def crear_catalogo_roles():
    """
    crea o actualiza en bd los roles iniciales del sistema (`roles.ROLES_INICIALES`) y
    sus permisos granulares (`roles.PERMISOS_POR_ROL`). idempotente: se llama tanto desde
    la migración de datos que introdujo este esquema como desde la señal `post_migrate`
    (`apps.py`) y desde `seed.py`, así que ampliar el catálogo en `roles.py` más adelante
    no requiere una migración nueva. no toca `Rol.name` de un rol ya existente (podría
    haberlo renombrado un administrador desde el admin).

    devuelve `{codigo: Rol}` para quien necesite resolver el rol recién creado/actualizado.
    """
    content_type = ContentType.objects.get_for_model(PermisoPersonalizado)
    permisos_por_codename = {
        codename: Permission.objects.get_or_create(
            content_type=content_type, codename=codename,
            defaults={'name': f'Puede: {codename}'},
        )[0]
        for codename in CATALOGO_PERMISOS
    }

    roles_por_codigo = {}
    for codigo, datos in ROLES_INICIALES.items():
        perfil = RolPerfil.objects.select_related('rol').filter(codigo=codigo).first()
        if perfil is None:
            rol = Rol.objects.create(name=datos['nombre'])
            # intenta crear con redireccion_login; si el campo no existe aún
            # (pre-migración 0005), captura TypeError y lo crea sin ese parámetro.
            try:
                perfil = RolPerfil.objects.create(
                    rol=rol, codigo=codigo, requiere_clinica=datos['requiere_clinica'],
                    redireccion_login=datos.get('redireccion_login', ''),
                )
            except TypeError:
                # campo redireccion_login no existe aún; se rellenará luego en 0005.
                perfil = RolPerfil.objects.create(
                    rol=rol, codigo=codigo, requiere_clinica=datos['requiere_clinica'],
                )
        else:
            rol = perfil.rol
            perfil.requiere_clinica = datos['requiere_clinica']
            # nota: `redireccion_login` NO se sincroniza en updates, solo en creación. es una
            # preferencia de enrutamiento que un administrador debe poder cambiar desde /admin/
            # sin que el próximo migrate/seed se la pise (igual criterio que Rol.name).
            perfil.save(update_fields=['requiere_clinica'])
        rol.permissions.set(
            permisos_por_codename[codename] for codename in PERMISOS_POR_ROL.get(codigo, set())
        )
        roles_por_codigo[codigo] = rol
    return roles_por_codigo


def obtener_datos_me(usuario):
    """
    arma el payload de `GET /api/v1/auth/me/` (prompt.md §13): usuario + grupo +
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
        rol_codigo = asignacion.rol.perfil.codigo
        clinics.extend(
            {'id': c.id, 'nombre': c.nombre, 'codigo': c.codigo, 'rol': rol_codigo}
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
        'roles': [a.rol.perfil.codigo for a in asignaciones],
    }


def codigos_permisos_de_usuario(usuario):
    """devuelve el `set` de codenames de permiso que concede alguno de los roles del
    usuario, en una única query (sin n+1). el superusuario recibe el catálogo completo.

    resulta útil para exponer los permisos al template (context processor) o para
    precalcular un mapa de permisos sin consultar `usuario_tiene_permiso()` permiso a
    permiso.
    """
    if usuario.is_superuser:
        return set(CATALOGO_PERMISOS)
    return set(
        UsuarioClinica.objects.filter(usuario=usuario)
        .values_list('rol__permissions__codename', flat=True)
        .distinct(),
    )


def usuario_tiene_permiso(usuario, clinica, permiso):
    """
    punto único de autorización (arquitectura.md §6, problema 2): tanto la ui html
    como la api deben resolver permisos llamando a esta función, nunca reimplementando
    la regla por su cuenta.

    comprueba los roles del usuario en `clinica` (o de alcance grupo/plataforma, que
    aplican a cualquier clínica del mismo grupo) y si alguno concede `permiso`, resolviendo
    directamente contra `auth_group_permissions`/`auth_permission` (ya no hay un catálogo
    en memoria: los permisos de cada rol se gestionan en bd, ver `crear_catalogo_roles()`).
    """
    if usuario.is_superuser:
        return True
    # la asignación aplica si es para esa clínica exacta o si es un rol de alcance
    # grupo/plataforma (`clinica=None`), que cubre cualquier clínica del grupo.
    return UsuarioClinica.objects.filter(usuario=usuario).filter(
        Q(clinica=clinica) | Q(clinica__isnull=True),
    ).filter(rol__permissions__codename=permiso).exists()


def usuario_tiene_permiso_generico(usuario, permiso):
    """
    comprueba si `usuario` tiene, en cualquiera de sus asignaciones (cualquier clínica o
    de alcance grupal), un rol que conceda `permiso`.

    usar cuando no hay una clínica concreta sobre la que resolver (listados/altas de recursos
    de alcance grupo, como grupo/clínica/especialidad); para permisos ligados a una clínica en
    concreto seguir usando `usuario_tiene_permiso()`.
    """
    if usuario.is_superuser:
        return True
    return UsuarioClinica.objects.filter(
        usuario=usuario, rol__permissions__codename=permiso,
    ).exists()


def obtener_rol_perfil_prioritario(usuario):
    """
    devuelve el `RolPerfil` que determina el destino post-login de `usuario`, según
    `roles.PRIORIDAD_ROLES_LOGIN` (GROUP_ADMIN > CLINIC_ADMIN > DOCTOR > RECEPTIONIST):
    el primero de esa lista que el usuario tenga asignado en alguna de sus
    `UsuarioClinica`, sin importar en cuántas clínicas o con qué otros roles conviva.

    devuelve `None` si el usuario no tiene ningún rol asignado (o solo tiene roles fuera
    de `PRIORIDAD_ROLES_LOGIN`, caso hoy imposible con el catálogo actual pero que se
    contempla de cara a roles futuros).
    """
    codigos_usuario = set(listar_roles_de_usuario(usuario))
    for codigo in PRIORIDAD_ROLES_LOGIN:
        if codigo in codigos_usuario:
            return RolPerfil.objects.get(codigo=codigo)
    return None


def url_post_login(usuario):
    """
    resuelve la url a la que redirigir a `usuario` justo tras iniciar sesión (ver
    `views.LoginPorRolView`).

    - superusuario: siempre `/admin/`, sin mirar sus roles (mismo criterio que
      `usuario_tiene_permiso()`: el superusuario es un caso aparte, no un rol).
    - con rol: `RolPerfil.redireccion_login` del rol ganador (`obtener_rol_perfil_prioritario`).
    - sin rol asignado, o rol ganador sin `redireccion_login` configurado, o
      `redireccion_login` apunta a un url name que ya no existe (catálogo desincronizado
      o valor corrupto editado a mano desde el admin): `None`. quien llama (la vista de
      login) debe tratarlo como "sin destino": no autenticar y mostrar un mensaje, nunca
      redirigir a una url inexistente ni dejar al usuario "colgado".
    """
    if usuario.is_superuser:
        return reverse('admin:index')
    perfil = obtener_rol_perfil_prioritario(usuario)
    if perfil is None or not perfil.redireccion_login:
        return None
    try:
        return reverse(perfil.redireccion_login)
    except NoReverseMatch:
        return None
