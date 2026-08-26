"""viewsets de la api de organizacion; todo acceso al orm pasa por services.py."""
from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError

from apps.organizacion import services
from apps.organizacion.api.serializers import (
    ClinicaSerializer,
    EspecialidadSerializer,
    GrupoSerializer,
)
from apps.organizacion.exceptions import CodigoDuplicadoError
from apps.organizacion.filters import ClinicaFilter, EspecialidadFilter, GrupoFilter


class IsStaffOrReadOnly(permissions.BasePermission):
    """fase 3 (provisional, hasta el sistema de roles de fase 4):
    lectura para cualquier autenticado, escritura solo para staff/superadmin.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_staff)


class GrupoViewSet(viewsets.ModelViewSet):
    """gestión de grupos; restringido a staff (dato de plataforma, no de un tenant)."""

    serializer_class = GrupoSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_class = GrupoFilter
    search_fields = ['nombre', 'codigo']
    ordering_fields = ['nombre', 'codigo', 'created_at']

    def get_queryset(self):
        return services.listar_grupos()

    def perform_create(self, serializer):
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
    """gestión de clínicas; lectura para autenticados, escritura solo staff."""

    serializer_class = ClinicaSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_class = ClinicaFilter
    search_fields = ['nombre', 'codigo', 'ciudad']
    ordering_fields = ['nombre', 'codigo', 'created_at']

    def get_queryset(self):
        return services.listar_clinicas()

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
    """gestión del catálogo de especialidades; lectura para autenticados, escritura solo staff."""

    serializer_class = EspecialidadSerializer
    permission_classes = [IsStaffOrReadOnly]
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
