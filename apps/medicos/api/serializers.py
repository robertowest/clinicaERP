from rest_framework import serializers

from apps.medicos.models import Medico, MedicoAusencia, MedicoClinicaEspecialidad
from apps.organizacion import services as organizacion_services
from apps.usuarios import services as usuarios_services


class MedicoClinicaEspecialidadSerializer(serializers.ModelSerializer):
    """asignación de especialidad por clínica, de solo lectura desde `MedicoSerializer`
    (mismo criterio que `UsuarioClinicaSerializer.accesos` en `apps.usuarios`: la gestión
    de alta/baja vive solo en la ui htmx, no en la api todavía)."""

    clinica_nombre = serializers.CharField(source='clinica.nombre', read_only=True)
    especialidad_nombre = serializers.CharField(source='especialidad.nombre', read_only=True)

    class Meta:
        model = MedicoClinicaEspecialidad
        fields = ['id', 'clinica', 'clinica_nombre', 'especialidad', 'especialidad_nombre']
        read_only_fields = ['id']


class MedicoSerializer(serializers.ModelSerializer):
    """el queryset de `grupo`/`usuario` viene de `organizacion.services`/`usuarios.services`,
    nunca de `Model.objects`.

    el campo `grupo` se oculta para usuarios no-superusuario en `__init__`: solo tienen una
    opción posible (su propio grupo), así que el viewset lo asigna automáticamente en
    `perform_create` en vez de exponerlo como elección (mismo criterio que `PacienteSerializer`).
    """

    grupo = serializers.PrimaryKeyRelatedField(queryset=organizacion_services.listar_grupos())
    grupo_nombre = serializers.CharField(source='grupo.nombre', read_only=True)
    usuario = serializers.PrimaryKeyRelatedField(queryset=usuarios_services.listar_usuarios())
    nombre_completo = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    clinicas = MedicoClinicaEspecialidadSerializer(
        source='asignaciones_clinica', many=True, read_only=True,
    )

    class Meta:
        model = Medico
        fields = [
            'id', 'grupo', 'grupo_nombre', 'usuario', 'nombre_completo', 'email', 'colegiado',
            'telefono', 'clinicas', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request is not None and request.user.is_authenticated and not request.user.is_superuser:
            self.fields.pop('grupo')


class MedicoAusenciaSerializer(serializers.ModelSerializer):
    """serializer de ausencias de médicos: el campo `medico` se acota al grupo del usuario
    en __init__ (mismo criterio que `MedicoSerializer`)."""

    medico_nombre = serializers.CharField(source='medico.nombre_completo', read_only=True)
    medico_grupo = serializers.CharField(source='medico.grupo.nombre', read_only=True)
    motivo_display = serializers.CharField(source='get_motivo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = MedicoAusencia
        fields = [
            'id', 'medico', 'medico_nombre', 'medico_grupo', 'fecha_inicio', 'fecha_fin',
            'motivo', 'motivo_display', 'estado', 'estado_display',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request is not None and request.user.is_authenticated and not request.user.is_superuser:
            self.fields['medico'].queryset = Medico.objects.filter(
                grupo=request.user.grupo,
            )
