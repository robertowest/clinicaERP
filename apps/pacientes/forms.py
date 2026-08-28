"""formularios de pacientes; el queryset de los campos relacionados se obtiene vía
services.py, nunca de Model.objects (mismo criterio que api/serializers.py).

ningún form persiste directamente: la vista llama a services.crear_paciente/
actualizar_paciente en form_valid y traduce NhcDuplicadoError/DocumentoDuplicadoError a
errores de formulario.
"""

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Field
from django import forms

from apps.organizacion import services as organizacion_services
from apps.pacientes.models import Paciente


class PacienteForm(forms.ModelForm):
    """el campo `grupo` solo se muestra a superusuario: el resto de roles (GROUP_ADMIN,
    CLINIC_ADMIN, DOCTOR, RECEPTIONIST) solo tienen una opción posible (su propio grupo), así
    que se oculta y la vista asigna `grupo=usuario.grupo` automáticamente en `form_valid`.
    """

    grupo = forms.ModelChoiceField(
        label='Grupo ',
        queryset=organizacion_services.listar_grupos()
    )

    class Meta:
        model = Paciente
        fields = [
            'grupo',
            'nhc',
            'nombre',
            'apellido',
            'documento_tipo',
            'documento_numero',
            'fecha_nacimiento',
            'sexo',
            'email',
            'telefono',
            'domicilio',
            'ciudad',
            'codigo_postal',
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)

        if usuario is not None and not usuario.is_superuser:
            del self.fields['grupo']

        self.helper = FormHelper(self)
        self.helper.form_tag = False

        self.helper.layout = Layout(
            'grupo',
            Row(
                Field('nombre', wrapper_class='col-md-6'),
                Field('apellido', wrapper_class='col-md-6'),
            ),
            Row(
                Field('nhc', wrapper_class='col-md-4'),
                Field('documento_tipo', wrapper_class='col-md-4'),
                Field('documento_numero', wrapper_class='col-md-4'),
            ),
            Row(
                Field('fecha_nacimiento', wrapper_class='col-md-6'),
                Field('sexo', wrapper_class='col-md-6'),
            ),

            'email',
            'telefono',
            Row(
                Field('domicilio', wrapper_class='col-md-5'),
                Field('ciudad', wrapper_class='col-md-5'),
                Field('codigo_postal', wrapper_class='col-md-2'),
            ),
        )
