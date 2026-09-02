"""tablas django-tables2 de medicos y ausencias; columnas alineadas con admin.py."""

import django_tables2 as tables

from apps.core.utils import ActiveColumn
from apps.medicos.models import Medico, MedicoAusencia

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


class MedicoAusenciaTable(tables.Table):
    medico_nombre = tables.Column(
        accessor='medico__usuario__username', verbose_name='médico',
        order_by=('medico__usuario__last_name', 'medico__usuario__first_name'),
    )
    colegiado = tables.Column(
        accessor='medico__colegiado', verbose_name='colegiado',
        order_by=('medico__colegiado',),
    )
    motivo = tables.Column(accessor='get_motivo_display', verbose_name='motivo')
    estado = tables.Column(accessor='get_estado_display', verbose_name='estado')
    is_active = ActiveColumn(verbose_name='activo')
    acciones = tables.TemplateColumn(
        template_name='crud/_acciones_columna.html',
        orderable=False,
        verbose_name='',
        extra_context={
            'url_prefix': 'medicos:ausencia',
            'edicion_pagina_completa': False,
            'permiso_editar': 'doctors.update',
            'permiso_eliminar': 'doctors.delete',
        },
    )

    class Meta:
        model = MedicoAusencia
        fields = ['fecha_inicio', 'fecha_fin']
        sequence = [
            'medico_nombre', 'colegiado', 'fecha_inicio', 'fecha_fin',
            'motivo', 'estado', 'is_active', 'acciones',
        ]
        attrs = ATRIBUTOS_TABLA
        template_name = 'django_tables2/bootstrap5.html'
