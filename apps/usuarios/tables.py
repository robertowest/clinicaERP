"""tablas django-tables2 de usuarios; columnas alineadas con admin.py."""

import django_tables2 as tables

from apps.core.utils import ActiveColumn, BooleandColumn
from apps.usuarios.models import CustomUser

ATRIBUTOS_TABLA = {'class': 'table table-hover align-middle mb-0'}


class UsuarioTable(tables.Table):
    username        = tables.Column(verbose_name='Usuario')
    nombre_completo = tables.Column(empty_values=(), verbose_name='nombre', orderable=False)
    email           = tables.Column(verbose_name='eMail', orderable=False)
    grupo           = tables.Column(accessor='grupo__nombre', verbose_name='grupo', default='—')
    is_staff        = BooleandColumn(verbose_name='Empleado', orderable=False)
    is_active       = ActiveColumn(verbose_name='estado', orderable=False)
    acciones        = tables.TemplateColumn(
        template_name='crud/_acciones_columna.html',
        orderable=False,
        verbose_name='',
        extra_context={
            'url_prefix': 'usuarios:usuario',
            'edicion_pagina_completa': False,
            'mostrar_gestion_accesos': True,
            'url_gestion_accesos_name': 'usuarios:usuario-accesos',
            'permiso_editar': 'users.manage',
            'permiso_eliminar': 'users.manage',
        },
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'grupo', 'is_staff', 'is_active']
        sequence = [
            'username', 'nombre_completo', 'email', 'grupo', 'is_staff', 'is_active', 'acciones',
        ]
        attrs = ATRIBUTOS_TABLA
        template_name = 'django_tables2/bootstrap5.html'

    def render_nombre_completo(self, record):
        return record.get_full_name() or '—'
