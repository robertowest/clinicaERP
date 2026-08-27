"""formularios de organizacion; el queryset de los campos relacionados se obtiene vía
services.py, nunca de Model.objects (mismo criterio que api/serializers.py).

ningún form persiste directamente: las vistas llaman a services.crear_*/actualizar_*
en form_valid y traducen CodigoDuplicadoError a errores de formulario.
"""

from crispy_forms.helper import FormHelper
from django import forms

from apps.organizacion import services
from apps.organizacion.models import Clinica, Especialidad, Grupo


class GrupoForm(forms.ModelForm):
    class Meta:
        model = Grupo
        fields = ['nombre', 'codigo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False


class EspecialidadForm(forms.ModelForm):
    class Meta:
        model = Especialidad
        fields = ['nombre', 'profesion', 'imagen']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False


class ClinicaForm(forms.ModelForm):
    """el queryset de `grupo` se acota al alcance del usuario en `__init__` (nunca a todos los
    grupos de la plataforma): evita que, por ejemplo, un `GROUP_ADMIN` cree o reasigne una
    clínica a un grupo ajeno eligiéndolo directamente en el formulario.
    """

    grupo = forms.ModelChoiceField(label='grupo', queryset=services.listar_grupos())
    especialidades = forms.ModelMultipleChoiceField(
        label='especialidades',
        queryset=services.listar_especialidades(),
        required=False,
        widget=forms.SelectMultiple(attrs={'size': 8}),
    )

    class Meta:
        model = Clinica
        fields = [
            'grupo',
            'nombre',
            'codigo',
            'domicilio',
            'ciudad',
            'codigo_postal',
            'telefono',
            'email',
            'especialidades',
        ]

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario is not None:
            self.fields['grupo'].queryset = services.listar_grupos_visibles_para(usuario)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
