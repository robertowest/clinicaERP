"""viewset de la api de medicos; todo acceso al orm pasa por services.py."""
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from apps.medicos import services
from apps.medicos.api.serializers import MedicoSerializer
from apps.medicos.exceptions import (
    ColegiadoDuplicadoError,
    UsuarioFueraDeGrupoError,
    UsuarioYaEsMedicoError,
)
from apps.medicos.filters import MedicoFilter
from apps.usuarios.permissions import permiso_por_accion


class MedicoViewSet(viewsets.ModelViewSet):
    """gestión de médicos: superusuario ve todos; el resto ve los de su propio grupo (ver
    `services.listar_medicos_visibles_para`). permisos granulares por acción (igual esquema
    que `PacienteViewSet`): `doctors.view/create/update/delete`.
    """

    serializer_class = MedicoSerializer
    permission_classes = [permiso_por_accion(
        ver='doctors.view', crear='doctors.create',
        actualizar='doctors.update', eliminar='doctors.delete',
    )]
    filterset_class = MedicoFilter
    search_fields = ['colegiado', 'usuario__first_name', 'usuario__last_name']
    ordering_fields = ['colegiado', 'created_at']

    def get_queryset(self):
        return services.listar_medicos_visibles_para(self.request.user)

    def perform_create(self, serializer):
        datos = dict(serializer.validated_data)
        if not self.request.user.is_superuser:
            datos['grupo'] = self.request.user.grupo
        try:
            serializer.instance = services.crear_medico(**datos)
        except (ColegiadoDuplicadoError, UsuarioFueraDeGrupoError, UsuarioYaEsMedicoError) as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc

    def perform_update(self, serializer):
        try:
            serializer.instance = services.actualizar_medico(
                serializer.instance, **serializer.validated_data,
            )
        except ColegiadoDuplicadoError as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc

    def perform_destroy(self, instance):
        services.desactivar_medico(instance)
