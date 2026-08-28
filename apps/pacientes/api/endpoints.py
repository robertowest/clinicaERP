"""viewset de la api de pacientes; todo acceso al orm pasa por services.py."""
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from apps.pacientes import services
from apps.pacientes.api.serializers import PacienteSerializer
from apps.pacientes.exceptions import DocumentoDuplicadoError, NhcDuplicadoError
from apps.pacientes.filters import PacienteFilter
from apps.usuarios.permissions import permiso_por_accion


class PacienteViewSet(viewsets.ModelViewSet):
    """gestión de pacientes: superusuario ve todos; el resto ve los de su propio grupo (ver
    `services.listar_pacientes_visibles_para`). permisos granulares por acción (a diferencia
    del esquema view/manage de `organizacion`): `patients.view/create/update/delete`.
    """

    serializer_class = PacienteSerializer
    permission_classes = [permiso_por_accion(
        ver='patients.view', crear='patients.create',
        actualizar='patients.update', eliminar='patients.delete',
    )]
    filterset_class = PacienteFilter
    search_fields = ['nombre', 'apellido', 'documento_numero', 'nhc']
    ordering_fields = ['nombre', 'apellido', 'nhc', 'fecha_nacimiento', 'created_at']

    def get_queryset(self):
        return services.listar_pacientes_visibles_para(self.request.user)

    def perform_create(self, serializer):
        datos = dict(serializer.validated_data)
        if not self.request.user.is_superuser:
            datos['grupo'] = self.request.user.grupo
        try:
            serializer.instance = services.crear_paciente(**datos)
        except (NhcDuplicadoError, DocumentoDuplicadoError) as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc

    def perform_update(self, serializer):
        try:
            serializer.instance = services.actualizar_paciente(
                serializer.instance, **serializer.validated_data,
            )
        except (NhcDuplicadoError, DocumentoDuplicadoError) as exc:
            raise ValidationError({'detail': [str(exc)]}) from exc

    def perform_destroy(self, instance):
        services.desactivar_paciente(instance)
