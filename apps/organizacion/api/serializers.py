from rest_framework import serializers

from apps.organizacion import services
from apps.organizacion.models import Clinica, Especialidad, Grupo


class GrupoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grupo
        fields = ['id', 'nombre', 'codigo', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class EspecialidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especialidad
        fields = ['id', 'nombre', 'profesion', 'imagen', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClinicaSerializer(serializers.ModelSerializer):
    """el queryset de los campos relacionados se obtiene vía services.py, nunca de Model.objects."""

    grupo = serializers.PrimaryKeyRelatedField(queryset=services.listar_grupos())
    grupo_nombre = serializers.CharField(source='grupo.nombre', read_only=True)
    especialidades = serializers.PrimaryKeyRelatedField(
        many=True, required=False, queryset=services.listar_especialidades(),
    )

    class Meta:
        model = Clinica
        fields = [
            'id', 'grupo', 'grupo_nombre', 'nombre', 'codigo', 'domicilio',
            'ciudad', 'codigo_postal', 'telefono', 'email', 'especialidades',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
