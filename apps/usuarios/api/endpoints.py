"""viewsets/vistas de la api de usuarios; todo acceso al orm pasa por services.py."""
from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.usuarios import services
from apps.usuarios.api.serializers import MeSerializer, UsuarioSerializer
from apps.usuarios.exceptions import UsuarioDuplicadoError
from apps.usuarios.filters import UsuarioFilter


class UsuarioViewSet(viewsets.ModelViewSet):
    """gestión de usuarios; restringida a staff (mismo criterio que GrupoViewSet)."""

    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_class = UsuarioFilter
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'date_joined']

    def get_queryset(self):
        return services.listar_usuarios()

    def perform_create(self, serializer):
        datos = dict(serializer.validated_data)
        password = datos.pop('password', None)
        if not password:
            mensaje = 'la contraseña es obligatoria al crear un usuario.'
            raise ValidationError({'password': [mensaje]})
        try:
            serializer.instance = services.crear_usuario(password=password, **datos)
        except UsuarioDuplicadoError as exc:
            raise ValidationError({'username': [str(exc)]}) from exc

    def perform_update(self, serializer):
        datos = dict(serializer.validated_data)
        password = datos.pop('password', None)
        try:
            serializer.instance = services.actualizar_usuario(serializer.instance, **datos)
        except UsuarioDuplicadoError as exc:
            raise ValidationError({'username': [str(exc)]}) from exc
        if password:
            services.cambiar_password(serializer.instance, password)

    def perform_destroy(self, instance):
        services.desactivar_usuario(instance)


class MeView(APIView):
    """`GET /api/v1/auth/me/`: usuario autenticado + grupo + clínicas accesibles + roles."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        datos = services.obtener_datos_me(request.user)
        return Response(MeSerializer(datos).data)
