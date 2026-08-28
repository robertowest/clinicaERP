"""tablas django-tables2 de pacientes; columnas alineadas con admin.py."""

import django_tables2 as tables

from apps.core.utils import ActiveColumn
from apps.pacientes.models import Paciente

ATRIBUTOS_TABLA = {'class': 'table table-hover align-middle mb-0'}


class PacienteTable(tables.Table):
    grupo = tables.Column(accessor='grupo__nombre', verbose_name='grupo')
    is_active = ActiveColumn(verbose_name='estado')
    acciones = tables.TemplateColumn(
        template_name='crud/_acciones_columna.html',
        orderable=False,
        verbose_name='',
        extra_context={
            'url_prefix': 'pacientes:paciente',
            'edicion_pagina_completa': True,
            'permiso_editar': 'patients.update',
            'permiso_eliminar': 'patients.delete',
        },
    )

    class Meta:
        model = Paciente
        fields = ['nhc', 'nombre', 'apellido', 'documento_numero', 'telefono']
        sequence = [
            'nhc', 'nombre', 'apellido', 'documento_numero', 'telefono', 'grupo', 'is_active',
            'acciones',
        ]
        attrs = ATRIBUTOS_TABLA
        template_name = 'django_tables2/bootstrap5.html'
