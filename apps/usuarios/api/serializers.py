"""serializers de usuarios; el queryset de los campos relacionados se obtiene vía
services.py, nunca de Model.objects (mismo criterio que forms.py)."""
from rest_framework import serializers

from apps.organizacion.services import listar_grupos
from apps.usuarios.models import CustomUser, UsuarioClinica


class UsuarioClinicaSerializer(serializers.ModelSerializer):
    clinica_nombre = serializers.CharField(source='clinica.nombre', read_only=True, default=None)

    class Meta:
        model = UsuarioClinica
        fields = ['id', 'clinica', 'clinica_nombre', 'rol']
        read_only_fields = ['id']


class UsuarioSerializer(serializers.ModelSerializer):
    """`password` es `write_only` y opcional: si se envía en un `PATCH`/`PUT`, la vista
    la pasa a `services.cambiar_password` en vez de guardarla tal cual (ver endpoints.py).
    """

    grupo = serializers.PrimaryKeyRelatedField(
        queryset=listar_grupos(), required=False, allow_null=True,
    )
    grupo_nombre = serializers.CharField(source='grupo.nombre', read_only=True, default=None)
    accesos = UsuarioClinicaSerializer(source='clinicas_asignadas', many=True, read_only=True)
    password = serializers.CharField(
        write_only=True, required=False, style={'input_type': 'password'},
    )

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'grupo', 'grupo_nombre',
            'accesos', 'is_staff', 'is_active', 'password',
        ]
        read_only_fields = ['id']


class GrupoResumenSerializer(serializers.Serializer):
    """subconjunto de `Grupo` para el bloque "group" de `/auth/me/` (prompt.md §13)."""

    id = serializers.IntegerField()
    nombre = serializers.CharField()
    codigo = serializers.CharField()


class ClinicaAccesoSerializer(serializers.Serializer):
    """una clínica accesible para el usuario autenticado, con su rol (bloque "clinics")."""

    id = serializers.IntegerField()
    nombre = serializers.CharField()
    codigo = serializers.CharField()
    rol = serializers.CharField()


class MeSerializer(serializers.Serializer):
    """respuesta de `GET /api/v1/auth/me/` (prompt.md §13): usuario + grupo + clínicas + roles."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    is_staff = serializers.BooleanField()
    group = GrupoResumenSerializer(allow_null=True)
    clinics = ClinicaAccesoSerializer(many=True)
    roles = serializers.ListField(child=serializers.CharField())
