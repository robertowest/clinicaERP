"""vistas html/htmx de organizacion: listados (django-tables2 + django-filter) y
formularios/confirmaciones en modal bootstrap (o página completa para clínica, por la
complejidad de su formulario). todo el acceso a datos pasa por services.py.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin

from apps.core.mixins import (
    HtmxTriggerMixin,
    ListaFiltradaMixin,
    StaffRequiredMixin,
    TituloContextMixin,
)
from apps.organizacion import services
from apps.organizacion.exceptions import CodigoDuplicadoError
from apps.organizacion.filters import ClinicaFilter, EspecialidadFilter, GrupoFilter
from apps.organizacion.forms import ClinicaForm, EspecialidadForm, GrupoForm
from apps.organizacion.tables import ClinicaTable, EspecialidadTable, GrupoTable

# --- Grupo -------------------------------------------------------------
# dato de plataforma (cruza tenants): restringido a staff incluso en lectura,
# igual que GrupoViewSet (permissions.IsAdminUser).


class GrupoListView(StaffRequiredMixin, ListaFiltradaMixin, SingleTableMixin, FilterView):
    table_class = GrupoTable
    filterset_class = GrupoFilter
    template_name = 'crud/list.html'
    paginate_by = 20
    titulo = 'Grupos'
    url_crear_name = 'organizacion:grupo-crear'

    def get_queryset(self):
        return services.listar_grupos()


class GrupoDetalleView(StaffRequiredMixin, DetailView):
    template_name = 'crud/detail_modal.html'
    context_object_name = 'objeto'
    titulo = 'Detalle del grupo'

    def get_object(self, queryset=None):
        return services.obtener_grupo(self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        grupo = context['objeto']
        context['titulo'] = self.titulo
        context['campos'] = [
            ('Nombre', grupo.nombre),
            ('Código', grupo.codigo),
            ('Estado', 'Activo' if grupo.is_active else 'Inactivo'),
            ('Creado', grupo.created_at),
        ]
        return context


class GrupoCreateView(StaffRequiredMixin, HtmxTriggerMixin, TituloContextMixin, CreateView):
    form_class = GrupoForm
    template_name = 'crud/form_modal.html'
    success_url = reverse_lazy('organizacion:grupo-list')
    titulo = 'Nuevo grupo'

    def form_valid(self, form):
        try:
            self.object = services.crear_grupo(**form.cleaned_data)
        except CodigoDuplicadoError as exc:
            form.add_error('codigo', str(exc))
            return self.form_invalid(form)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class GrupoUpdateView(StaffRequiredMixin, HtmxTriggerMixin, TituloContextMixin, UpdateView):
    form_class = GrupoForm
    template_name = 'crud/form_modal.html'
    success_url = reverse_lazy('organizacion:grupo-list')
    titulo = 'Editar grupo'

    def get_object(self, queryset=None):
        return services.obtener_grupo(self.kwargs['pk'])

    def form_valid(self, form):
        try:
            services.actualizar_grupo(self.object, **form.cleaned_data)
        except CodigoDuplicadoError as exc:
            form.add_error('codigo', str(exc))
            return self.form_invalid(form)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class GrupoBajaView(StaffRequiredMixin, HtmxTriggerMixin, TituloContextMixin, DeleteView):
    template_name = 'crud/confirm_delete_modal.html'
    success_url = reverse_lazy('organizacion:grupo-list')
    titulo = 'Desactivar grupo'

    def get_object(self, queryset=None):
        return services.obtener_grupo(self.kwargs['pk'])

    def form_valid(self, form):
        services.desactivar_grupo(self.object)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class GrupoReactivarView(StaffRequiredMixin, HtmxTriggerMixin, View):
    def post(self, request, pk):
        grupo = services.obtener_grupo(pk)
        services.reactivar_grupo(grupo)
        messages.success(request, f'Grupo «{grupo.nombre}» reactivado.')
        return self._respuesta_htmx() or HttpResponseRedirect(
            reverse_lazy('organizacion:grupo-list'),
        )


# --- Especialidad -------------------------------------------------------------
# catálogo global: lectura para cualquier autenticado, escritura solo staff.


class EspecialidadListView(LoginRequiredMixin, ListaFiltradaMixin, SingleTableMixin, FilterView):
    table_class = EspecialidadTable
    filterset_class = EspecialidadFilter
    template_name = 'crud/list.html'
    paginate_by = 20
    titulo = 'Especialidades'
    url_crear_name = 'organizacion:especialidad-crear'

    def get_queryset(self):
        return services.listar_especialidades()


class EspecialidadDetalleView(LoginRequiredMixin, DetailView):
    template_name = 'crud/detail_modal.html'
    context_object_name = 'objeto'
    titulo = 'Detalle de la especialidad'

    def get_object(self, queryset=None):
        return services.obtener_especialidad(self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        especialidad = context['objeto']
        context['titulo'] = self.titulo
        context['campos'] = [
            ('Nombre', especialidad.nombre),
            ('Profesión', especialidad.profesion or '—'),
            ('Estado', 'Activa' if especialidad.is_active else 'Inactiva'),
        ]
        return context


class EspecialidadCreateView(
    StaffRequiredMixin,
    HtmxTriggerMixin,
    TituloContextMixin,
    CreateView,
):
    form_class = EspecialidadForm
    template_name = 'crud/form_modal.html'
    success_url = reverse_lazy('organizacion:especialidad-list')
    titulo = 'Nueva especialidad'

    def form_valid(self, form):
        try:
            self.object = services.crear_especialidad(**form.cleaned_data)
        except CodigoDuplicadoError as exc:
            form.add_error('nombre', str(exc))
            return self.form_invalid(form)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class EspecialidadUpdateView(
    StaffRequiredMixin,
    HtmxTriggerMixin,
    TituloContextMixin,
    UpdateView,
):
    form_class = EspecialidadForm
    template_name = 'crud/form_modal.html'
    success_url = reverse_lazy('organizacion:especialidad-list')
    titulo = 'Editar especialidad'

    def get_object(self, queryset=None):
        return services.obtener_especialidad(self.kwargs['pk'])

    def form_valid(self, form):
        services.actualizar_especialidad(self.object, **form.cleaned_data)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class EspecialidadBajaView(StaffRequiredMixin, HtmxTriggerMixin, TituloContextMixin, DeleteView):
    template_name = 'crud/confirm_delete_modal.html'
    success_url = reverse_lazy('organizacion:especialidad-list')
    titulo = 'Desactivar especialidad'

    def get_object(self, queryset=None):
        return services.obtener_especialidad(self.kwargs['pk'])

    def form_valid(self, form):
        services.desactivar_especialidad(self.object)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class EspecialidadReactivarView(StaffRequiredMixin, HtmxTriggerMixin, View):
    def post(self, request, pk):
        especialidad = services.obtener_especialidad(pk)
        services.reactivar_especialidad(especialidad)
        messages.success(request, f'Especialidad «{especialidad.nombre}» reactivada.')
        return self._respuesta_htmx() or HttpResponseRedirect(
            reverse_lazy('organizacion:especialidad-list'),
        )


# --- Clinica -------------------------------------------------------------
# lectura para cualquier autenticado, escritura solo staff. create/update usan página
# completa (crud/form_page.html): el formulario incluye 7 campos + m2m especialidades,
# demasiado para un modal cómodo.


class ClinicaListView(LoginRequiredMixin, ListaFiltradaMixin, SingleTableMixin, FilterView):
    table_class = ClinicaTable
    filterset_class = ClinicaFilter
    template_name = 'crud/list.html'
    paginate_by = 20
    titulo = 'Clínicas'
    url_crear_name = 'organizacion:clinica-crear'
    crear_en_pagina_completa = True

    def get_queryset(self):
        return services.listar_clinicas()


class ClinicaDetalleView(LoginRequiredMixin, DetailView):
    template_name = 'crud/detail_modal.html'
    context_object_name = 'objeto'
    titulo = 'Detalle de la clínica'

    def get_object(self, queryset=None):
        return services.obtener_clinica(self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clinica = context['objeto']
        context['titulo'] = self.titulo
        context['campos'] = [
            ('Grupo', clinica.grupo.nombre),
            ('Nombre', clinica.nombre),
            ('Código', clinica.codigo),
            ('Domicilio', clinica.domicilio or '—'),
            ('Ciudad', clinica.ciudad or '—'),
            ('Código postal', clinica.codigo_postal or '—'),
            ('Teléfono', clinica.telefono or '—'),
            ('Correo', clinica.email or '—'),
            (
                'Especialidades',
                ', '.join(e.nombre for e in clinica.especialidades.all()) or '—',
            ),
            ('Estado', 'Activa' if clinica.is_active else 'Inactiva'),
        ]
        return context


class ClinicaCreateView(StaffRequiredMixin, TituloContextMixin, CreateView):
    form_class = ClinicaForm
    template_name = 'crud/form_page.html'
    success_url = reverse_lazy('organizacion:clinica-list')
    titulo = 'Nueva clínica'
    url_cancelar_name = 'organizacion:clinica-list'

    def form_valid(self, form):
        try:
            self.object = services.crear_clinica(**form.cleaned_data)
        except CodigoDuplicadoError as exc:
            form.add_error('codigo', str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'Clínica «{self.object.nombre}» creada.')
        return HttpResponseRedirect(self.get_success_url())


class ClinicaUpdateView(StaffRequiredMixin, TituloContextMixin, UpdateView):
    form_class = ClinicaForm
    template_name = 'crud/form_page.html'
    success_url = reverse_lazy('organizacion:clinica-list')
    titulo = 'Editar clínica'
    url_cancelar_name = 'organizacion:clinica-list'

    def get_object(self, queryset=None):
        return services.obtener_clinica(self.kwargs['pk'])

    def form_valid(self, form):
        try:
            services.actualizar_clinica(self.object, **form.cleaned_data)
        except CodigoDuplicadoError as exc:
            form.add_error('codigo', str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'Clínica «{self.object.nombre}» actualizada.')
        return HttpResponseRedirect(self.get_success_url())


class ClinicaBajaView(StaffRequiredMixin, HtmxTriggerMixin, TituloContextMixin, DeleteView):
    template_name = 'crud/confirm_delete_modal.html'
    success_url = reverse_lazy('organizacion:clinica-list')
    titulo = 'Desactivar clínica'

    def get_object(self, queryset=None):
        return services.obtener_clinica(self.kwargs['pk'])

    def form_valid(self, form):
        services.desactivar_clinica(self.object)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class ClinicaReactivarView(StaffRequiredMixin, HtmxTriggerMixin, View):
    def post(self, request, pk):
        clinica = services.obtener_clinica(pk)
        services.reactivar_clinica(clinica)
        messages.success(request, f'Clínica «{clinica.nombre}» reactivada.')
        return self._respuesta_htmx() or HttpResponseRedirect(
            reverse_lazy('organizacion:clinica-list'),
        )
