"""formularios de usuarios; el queryset de los campos relacionados se obtiene vía
services.py, nunca de Model.objects (mismo criterio que api/serializers.py).

ningún form persiste directamente: las vistas llaman a services.crear_usuario/
actualizar_usuario/asignar_rol en form_valid y traducen las excepciones de dominio a
errores de formulario.
"""
from crispy_forms.helper import FormHelper
from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.organizacion.services import listar_clinicas, listar_grupos
from apps.usuarios.models import CustomUser, UsuarioClinica
from apps.usuarios.roles import Roles


class UsuarioForm(forms.ModelForm):
    """edición de un usuario existente: nunca incluye la contraseña (ver
    `UsuarioCreateForm` y `services.cambiar_password`)."""

    grupo = forms.ModelChoiceField(
        label='Grupo', queryset=listar_grupos(), required=False,
        help_text='vacío solo para el superadministrador de plataforma.',
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'grupo', 'is_staff', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False


class UsuarioCreateForm(UsuarioForm):
    """alta de usuario: añade contraseña (no es un campo de `Meta.fields`: se valida y
    se pasa a `services.crear_usuario`, que la hashea con `set_password`)."""

    password1 = forms.CharField(label='contraseña', widget=forms.PasswordInput)
    password2 = forms.CharField(label='confirmar contraseña', widget=forms.PasswordInput)

    field_order = [
        'username', 'email', 'first_name', 'last_name', 'grupo',
        'password1', 'password2', 'is_staff', 'is_active',
    ]

    def clean(self):
        datos = super().clean()
        password1 = datos.get('password1')
        password2 = datos.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'las contraseñas no coinciden.')
            return datos
        if password1:
            try:
                password_validation.validate_password(password1)
            except DjangoValidationError as exc:
                self.add_error('password1', exc)
        return datos


class UsuarioClinicaForm(forms.ModelForm):
    """asigna un rol a un usuario, opcionalmente ligado a una clínica de su grupo.

    el queryset de `clinica` se acota al grupo del usuario desde la vista (`__init__`),
    la validación de fondo (rol vs. clínica) vive en `services.asignar_rol`.
    """

    rol = forms.ChoiceField(label='rol', choices=Roles.choices)

    class Meta:
        model = UsuarioClinica
        fields = ['clinica', 'rol']

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['clinica'].required = False
        if usuario is not None:
            self.fields['clinica'].queryset = listar_clinicas(grupo=usuario.grupo)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
