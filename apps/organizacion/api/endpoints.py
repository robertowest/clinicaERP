"""viewsets de la api de organizacion; todo acceso al orm pasa por services.py."""
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.organizacion import services
from apps.organizacion.api.serializers import (
    ClinicaSerializer,
    EspecialidadSerializer,
    GrupoSerializer,
)
from apps.organizacion.exceptions import CodigoDuplicadoError
from apps.organizacion.filters import ClinicaFilter, EspecialidadFilter, GrupoFilter
from apps.usuarios.permissions import permiso_por_metodo


class GrupoViewSet(viewsets.ModelViewSet):
    """gestión de grupos: superusuario ve todos; `GROUP_ADMIN` solo el suyo (ver
    `services.listar_grupos_visibles_para`)."""

    serializer_class = GrupoSerializer
    permission_classes = [permiso_por_metodo('groups.view', 'groups.manage')]
    filterset_class = GrupoFilter
    search_fields = ['nombre', 'codigo']
    ordering_fields = ['nombre', 'codigo', 'created_at']

    def get_queryset(self):
        return services.listar_grupos_visibles_para(self.request.user)

    def perform_create(self, serializer):
        # crear un grupo da de alta un tenant nuevo: aunque groups.manage permite editar el
        # propio grupo, dar de alta uno nuevo sigue siendo una operación de plataforma
        # exclusiva de superadmin (si no, cualquier group_admin podría generar tenants sin
        # límite).
        if not self.request.user.is_superuser:
            raise PermissionDenied('solo un superadministrador puede crear grupos nuevos.')
        try:
            serializer.instance = services.crear_grupo(**serializer.validated_data)
        except CodigoDuplicadoError as exc:
            raise ValidationError({'codigo': [str(exc)]}) from exc

    def perform_update(self, serializer):
        try:
            serializer.instance = services.actualizar_grupo(
                serializer.instance, **serializer.validated_data,
            )
        except CodigoDuplicadoError as exc:
            raise ValidationError({'codigo': [str(exc)]}) from exc

    def perform_destroy(self, instance):
        services.desactivar_grupo(instance)


class ClinicaViewSet(viewsets.ModelViewSet):
    """gestión de clínicas: superusuario ve todas; `GROUP_ADMIN` las de su grupo;
    `CLINIC_ADMIN` solo las que tiene asignadas (ver `services.listar_clinicas_visibles_para`).
    """

    serializer_class = ClinicaSerializer
    permission_classes = [permiso_por_metodo('clinics.view', 'clinics.manage')]
    filterset_class = ClinicaFilter
    search_fields = ['nombre', 'codigo', 'ciudad']
    ordering_fields = ['nombre', 'codigo', 'created_at']

    def get_queryset(self):
        return services.listar_clinicas_visibles_para(self.request.user)

    def perform_create(self, serializer):
        try:
            serializer.instance = services.crear_clinica(**serializer.validated_data)
        except CodigoDuplicadoError as exc:
            raise ValidationError({'codigo': [str(exc)]}) from exc

    def perform_update(self, serializer):
        try:
            serializer.instance = services.actualizar_clinica(
                serializer.instance, **serializer.validated_data,
            )
        except CodigoDuplicadoError as exc:
            raise ValidationError({'codigo': [str(exc)]}) from exc

    def perform_destroy(self, instance):
        services.desactivar_clinica(instance)


class EspecialidadViewSet(viewsets.ModelViewSet):
    """gestión del catálogo global de especialidades (sin scoping por grupo/clínica)."""

    serializer_class = EspecialidadSerializer
    permission_classes = [permiso_por_metodo('specialties.view', 'specialties.manage')]
    filterset_class = EspecialidadFilter
    search_fields = ['nombre', 'codigo']
    ordering_fields = ['nombre', 'codigo']

    def get_queryset(self):
        return services.listar_especialidades()

    def perform_create(self, serializer):
        try:
            serializer.instance = services.crear_especialidad(**serializer.validated_data)
        except CodigoDuplicadoError as exc:
            raise ValidationError({'nombre': [str(exc)]}) from exc

    def perform_update(self, serializer):
        serializer.instance = services.actualizar_especialidad(
            serializer.instance, **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        services.desactivar_especialidad(instance)
