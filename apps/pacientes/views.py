"""vistas html/htmx de pacientes: listado (django-tables2 + django-filter) y formulario en
página completa (13 campos, demasiados para un modal cómodo, mismo criterio que Clinica) +
detalle/baja en modal bootstrap. todo el acceso a datos pasa por services.py.
"""

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin

from apps.core.mixins import HtmxTriggerMixin, ListaFiltradaMixin, TituloContextMixin
from apps.pacientes import services
from apps.pacientes.exceptions import DocumentoDuplicadoError, NhcDuplicadoError
from apps.pacientes.filters import PacienteFilter
from apps.pacientes.forms import PacienteForm
from apps.pacientes.tables import PacienteTable
from apps.usuarios.mixins import PermisoRequeridoMixin

# superusuario ve todos los pacientes; el resto ve los de su propio grupo (ver
# services.listar_pacientes_visibles_para). permisos granulares por acción: patients.view
# (list/detalle), patients.create, patients.update, patients.delete (baja/reactivar).


class PacienteListView(PermisoRequeridoMixin, ListaFiltradaMixin, SingleTableMixin, FilterView):
    permiso_requerido = 'patients.view'
    table_class = PacienteTable
    filterset_class = PacienteFilter
    template_name = 'crud/list.html'
    paginate_by = 20
    titulo = 'Pacientes'
    url_crear_name = 'pacientes:paciente-crear'
    crear_en_pagina_completa = True

    def get_queryset(self):
        return services.listar_pacientes_visibles_para(self.request.user)


class PacienteDetalleView(PermisoRequeridoMixin, DetailView):
    permiso_requerido = 'patients.view'
    template_name = 'crud/detail_modal.html'
    context_object_name = 'objeto'
    titulo = 'Detalle del paciente'

    def get_object(self, queryset=None):
        return services.obtener_paciente_visible_para(self.kwargs['pk'], self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paciente = context['objeto']
        context['titulo'] = self.titulo
        context['campos'] = [
            ('Grupo', paciente.grupo.nombre),
            ('NHC', paciente.nhc),
            ('Nombre', paciente.nombre),
            ('Apellido', paciente.apellido),
            ('Documento', f'{paciente.get_documento_tipo_display()} {paciente.documento_numero}'),
            ('Fecha de nacimiento', paciente.fecha_nacimiento),
            ('Sexo', paciente.get_sexo_display()),
            ('Correo', paciente.email or '—'),
            ('Teléfono', paciente.telefono or '—'),
            ('Domicilio', paciente.domicilio or '—'),
            ('Ciudad', paciente.ciudad or '—'),
            ('Código postal', paciente.codigo_postal or '—'),
            ('Estado', 'Activo' if paciente.is_active else 'Inactivo'),
        ]
        return context


class PacienteCreateView(PermisoRequeridoMixin, TituloContextMixin, CreateView):
    permiso_requerido = 'patients.create'
    form_class = PacienteForm
    template_name = 'crud/form_page.html'
    success_url = reverse_lazy('pacientes:paciente-list')
    titulo = 'Nuevo paciente'
    url_cancelar_name = 'pacientes:paciente-list'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs

    def form_valid(self, form):
        datos = dict(form.cleaned_data)
        if 'grupo' not in datos:
            datos['grupo'] = self.request.user.grupo
        try:
            self.object = services.crear_paciente(**datos)
        except NhcDuplicadoError as exc:
            form.add_error('nhc', str(exc))
            return self.form_invalid(form)
        except DocumentoDuplicadoError as exc:
            form.add_error('documento_numero', str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'Paciente «{self.object}» creado.')
        return HttpResponseRedirect(self.get_success_url())


class PacienteUpdateView(PermisoRequeridoMixin, TituloContextMixin, UpdateView):
    permiso_requerido = 'patients.update'
    form_class = PacienteForm
    template_name = 'crud/form_page.html'
    success_url = reverse_lazy('pacientes:paciente-list')
    titulo = 'Editar paciente'
    url_cancelar_name = 'pacientes:paciente-list'

    def get_object(self, queryset=None):
        return services.obtener_paciente_visible_para(self.kwargs['pk'], self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            services.actualizar_paciente(self.object, **form.cleaned_data)
        except NhcDuplicadoError as exc:
            form.add_error('nhc', str(exc))
            return self.form_invalid(form)
        except DocumentoDuplicadoError as exc:
            form.add_error('documento_numero', str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'Paciente «{self.object}» actualizado.')
        return HttpResponseRedirect(self.get_success_url())


class PacienteBajaView(PermisoRequeridoMixin, HtmxTriggerMixin, TituloContextMixin, DeleteView):
    permiso_requerido = 'patients.delete'
    template_name = 'crud/confirm_delete_modal.html'
    success_url = reverse_lazy('pacientes:paciente-list')
    titulo = 'Desactivar paciente'

    def get_object(self, queryset=None):
        return services.obtener_paciente_visible_para(self.kwargs['pk'], self.request.user)

    def form_valid(self, form):
        services.desactivar_paciente(self.object)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class PacienteReactivarView(PermisoRequeridoMixin, HtmxTriggerMixin, View):
    permiso_requerido = 'patients.delete'

    def post(self, request, pk):
        paciente = services.obtener_paciente_visible_para(pk, request.user)
        services.reactivar_paciente(paciente)
        messages.success(request, f'Paciente «{paciente}» reactivado.')
        return self._respuesta_htmx() or HttpResponseRedirect(
            reverse_lazy('pacientes:paciente-list'),
        )
