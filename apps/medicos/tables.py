"""tablas django-tables2 de medicos; columnas alineadas con admin.py."""

import django_tables2 as tables

from apps.core.utils import ActiveColumn
from apps.medicos.models import Medico

ATRIBUTOS_TABLA = {'class': 'table table-hover align-middle mb-0'}


class MedicoTable(tables.Table):
    nombre_completo = tables.Column(
        accessor='nombre_completo', verbose_name='nombre',
        order_by=('usuario__last_name', 'usuario__first_name'),
    )
    grupo = tables.Column(accessor='grupo__nombre', verbose_name='grupo')
    is_active = ActiveColumn(verbose_name='estado')
    acciones = tables.TemplateColumn(
        template_name='crud/_acciones_columna.html',
        orderable=False,
        verbose_name='',
        extra_context={
            'url_prefix': 'medicos:medico',
            'edicion_pagina_completa': True,
            'permiso_editar': 'doctors.update',
            'permiso_eliminar': 'doctors.delete',
            'mostrar_gestion_accesos': True,
            'permiso_gestion_accesos': 'doctors.update',
            'url_gestion_accesos_name': 'medicos:medico-clinicas',
        },
    )

    class Meta:
        model = Medico
        fields = ['colegiado', 'telefono']
        sequence = ['nombre_completo', 'colegiado', 'telefono', 'grupo', 'is_active', 'acciones']
        attrs = ATRIBUTOS_TABLA
        template_name = 'django_tables2/bootstrap5.html'
