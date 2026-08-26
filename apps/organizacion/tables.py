"""tablas django-tables2 de organizacion; columnas alineadas con admin.py."""

import django_tables2 as tables

from apps.core.utils import BooleandColumn
from apps.organizacion.models import Clinica, Especialidad, Grupo

ATRIBUTOS_TABLA = {'class': 'table table-hover align-middle mb-0'}


class GrupoTable(tables.Table):
    is_active = BooleandColumn(verbose_name='estado')
    acciones = tables.TemplateColumn(
        template_name='crud/_acciones_columna.html',
        orderable=False,
        verbose_name='',
        extra_context={'url_prefix': 'organizacion:grupo'},
    )

    class Meta:
        model = Grupo
        fields = ['nombre', 'codigo', 'is_active']
        sequence = ['nombre', 'codigo', 'is_active', 'acciones']
        attrs = ATRIBUTOS_TABLA
        template_name = 'django_tables2/bootstrap5.html'


class EspecialidadTable(tables.Table):
    is_active = BooleandColumn(verbose_name='estado')
    acciones = tables.TemplateColumn(
        template_name='crud/_acciones_columna.html',
        orderable=False,
        verbose_name='',
        extra_context={'url_prefix': 'organizacion:especialidad'},
    )

    class Meta:
        model = Especialidad
        fields = ['nombre', 'profesion', 'is_active']
        sequence = ['nombre', 'profesion', 'is_active', 'acciones']
        attrs = ATRIBUTOS_TABLA
        template_name = 'django_tables2/bootstrap5.html'


class ClinicaTable(tables.Table):
    grupo = tables.Column(accessor='grupo__nombre', verbose_name='grupo')
    is_active = BooleandColumn(verbose_name='estado')
    acciones = tables.TemplateColumn(
        template_name='crud/_acciones_columna.html',
        orderable=False,
        verbose_name='',
        extra_context={'url_prefix': 'organizacion:clinica', 'edicion_pagina_completa': True},
    )

    class Meta:
        model = Clinica
        fields = ['nombre', 'codigo', 'grupo', 'ciudad', 'is_active']
        sequence = ['nombre', 'codigo', 'grupo', 'ciudad', 'is_active', 'acciones']
        attrs = ATRIBUTOS_TABLA
        template_name = 'django_tables2/bootstrap5.html'
