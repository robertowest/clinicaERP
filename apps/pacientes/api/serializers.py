from rest_framework import serializers

from apps.organizacion import services as organizacion_services
from apps.pacientes.models import Paciente


class PacienteSerializer(serializers.ModelSerializer):
    """el queryset de `grupo` viene de `organizacion.services`, nunca de `Model.objects`.

    el campo `grupo` se oculta para usuarios no-superusuario en `__init__`: solo tienen una
    opción posible (su propio grupo), así que el viewset lo asigna automáticamente en
    `perform_create` en vez de exponerlo como elección.
    """

    grupo = serializers.PrimaryKeyRelatedField(queryset=organizacion_services.listar_grupos())
    grupo_nombre = serializers.CharField(source='grupo.nombre', read_only=True)

    class Meta:
        model = Paciente
        fields = [
            'id', 'grupo', 'grupo_nombre', 'nhc', 'nombre', 'apellido', 'documento_tipo',
            'documento_numero', 'fecha_nacimiento', 'sexo', 'email', 'telefono', 'domicilio',
            'ciudad', 'codigo_postal', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request is not None and request.user.is_authenticated and not request.user.is_superuser:
            self.fields.pop('grupo')
