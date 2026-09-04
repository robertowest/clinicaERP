"""formularios de medicos y ausencias; el queryset de los campos relacionados se obtiene vía
services.py, nunca de Model.objects (mismo criterio que api/serializers.py).

ningún form persiste directamente: la vista llama a services.crear_medico/
actualizar_medico/crear_ausencia/actualizar_ausencia en form_valid y traduce las
excepciones de dominio a errores de formulario.
"""

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Row
from django import forms

from apps.medicos import services
from apps.medicos.models import Medico, MedicoAusencia, MedicoClinicaEspecialidad
from apps.organizacion import services as organizacion_services


class MedicoForm(forms.ModelForm):
    """el campo `grupo` solo se muestra a superusuario (mismo criterio que `PacienteForm`).

    el campo `usuario` solo se ofrece entre los usuarios sin médico asociado todavía
    (`services.listar_usuarios_disponibles`) y, en edición, se deshabilita: el vínculo 1:1
    no se reasigna desde el formulario.
    """

    grupo = forms.ModelChoiceField(
        label='Grupo', queryset=organizacion_services.listar_grupos(),
    )
    usuario = forms.ModelChoiceField(
        label='Usuario', queryset=services.listar_usuarios_disponibles(),
    )

    class Meta:
        model = Medico
        fields = ['grupo', 'usuario', 'tratamiento', 'colegiado', 'telefono']

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)

        if usuario is not None and not usuario.is_superuser:
            del self.fields['grupo']

        if self.instance.pk:
            # edición: el usuario ligado no se reasigna, y ya no está entre los
            # "disponibles" (tiene un médico: el propio `self.instance`).
            self.fields['usuario'].queryset = services.listar_usuarios_disponibles(
                grupo=self.instance.grupo, medico=self.instance,
            )
            self.fields['usuario'].disabled = True
        elif usuario is not None and not usuario.is_superuser:
            self.fields['usuario'].queryset = services.listar_usuarios_disponibles(
                grupo=usuario.grupo,
            )

        self.helper = FormHelper(self)
        self.helper.form_tag = False

        self.helper.layout = Layout(
            'grupo',
            'usuario',
            Row(
                Field('tratamiento', wrapper_class='col-2'),
                Field('colegiado', wrapper_class='col-5'),
                Field('telefono', wrapper_class='col-5'),
            ),
        )


class MedicoClinicaForm(forms.ModelForm):
    """asigna a un médico una especialidad en una clínica de su grupo.

    el queryset de `clinica` se acota al grupo del médico desde la vista (`__init__`), la
    validación de fondo (clínica vs. grupo, duplicado) vive en
    `services.asignar_clinica_especialidad`.
    """

    class Meta:
        model = MedicoClinicaEspecialidad
        fields = ['clinica', 'especialidad']

    def __init__(self, *args, medico=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['especialidad'].queryset = organizacion_services.listar_especialidades()
        if medico is not None:
            self.fields['clinica'].queryset = organizacion_services.listar_clinicas(
                grupo=medico.grupo,
            )
        self.helper = FormHelper(self)
        self.helper.form_tag = False


class MedicoAusenciaForm(forms.ModelForm):
    """formulario de ausencia de médico: médicos y fechas son obligatorios, motivo y estado
    tienen choices predefinidos. el queryset de `medico` se acota al grupo del usuario
    en no-superusuario (mismo criterio que `MedicoForm`)."""

    class Meta:
        model = MedicoAusencia
        fields = ['medico', 'fecha_inicio', 'fecha_fin', 'motivo', 'estado']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario is not None and not usuario.is_superuser:
            self.fields['medico'].queryset = services.listar_medicos(
                grupo=usuario.grupo,
            )
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            'medico',
            Row(
                Field('fecha_inicio', wrapper_class='col-md-6'),
                Field('fecha_fin', wrapper_class='col-md-6'),
            ),
            Row(
                Field('motivo', wrapper_class='col-md-6'),
                Field('estado', wrapper_class='col-md-6'),
            ),
        )
