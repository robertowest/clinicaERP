"""vistas html/htmx de organizacion: listados (django-tables2 + django-filter) y
formularios/confirmaciones en modal bootstrap (o página completa para clínica, por la
complejidad de su formulario). todo el acceso a datos pasa por services.py.
"""

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin

from apps.core.mixins import HtmxTriggerMixin, ListaFiltradaMixin, TituloContextMixin
from apps.organizacion import services
from apps.organizacion.exceptions import CodigoDuplicadoError
from apps.organizacion.filters import ClinicaFilter, EspecialidadFilter, GrupoFilter
from apps.organizacion.forms import ClinicaForm, EspecialidadForm, GrupoForm
from apps.organizacion.tables import ClinicaTable, EspecialidadTable, GrupoTable
from apps.usuarios.mixins import PermisoRequeridoMixin

# --- Grupo -------------------------------------------------------------
# superusuario ve todos los grupos; GROUP_ADMIN (único rol con permiso "groups.*") solo el
# suyo propio, igual que GrupoViewSet (ver services.listar_grupos_visibles_para).


class GrupoListView(PermisoRequeridoMixin, ListaFiltradaMixin, SingleTableMixin, FilterView):
    permiso_requerido = 'groups.view'
    table_class = GrupoTable
    filterset_class = GrupoFilter
    template_name = 'crud/list.html'
    paginate_by = 20
    titulo = 'Grupos'
    url_crear_name = 'organizacion:grupo-crear'

    def get_queryset(self):
        return services.listar_grupos_visibles_para(self.request.user)


class GrupoDetalleView(PermisoRequeridoMixin, DetailView):
    permiso_requerido = 'groups.view'
    template_name = 'crud/detail_modal.html'
    context_object_name = 'objeto'
    titulo = 'Detalle del grupo'

    def get_object(self, queryset=None):
        return services.obtener_grupo_visible_para(self.kwargs['pk'], self.request.user)

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


class GrupoCreateView(PermisoRequeridoMixin, HtmxTriggerMixin, TituloContextMixin, CreateView):
    # crear un grupo da de alta un tenant nuevo: sigue siendo exclusivo de superadmin aunque
    # groups.manage permita a GROUP_ADMIN editar su propio grupo (si no, cualquier
    # group_admin podría generar tenants sin límite).
    permiso_requerido = 'groups.manage'
    form_class = GrupoForm
    template_name = 'crud/form_modal.html'
    success_url = reverse_lazy('organizacion:grupo-list')
    titulo = 'Nuevo grupo'

    def test_func(self):
        return self.request.user.is_superuser

    def form_valid(self, form):
        try:
            self.object = services.crear_grupo(**form.cleaned_data)
        except CodigoDuplicadoError as exc:
            form.add_error('codigo', str(exc))
            return self.form_invalid(form)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class GrupoUpdateView(PermisoRequeridoMixin, HtmxTriggerMixin, TituloContextMixin, UpdateView):
    permiso_requerido = 'groups.manage'
    form_class = GrupoForm
    template_name = 'crud/form_modal.html'
    success_url = reverse_lazy('organizacion:grupo-list')
    titulo = 'Editar grupo'

    def get_object(self, queryset=None):
        return services.obtener_grupo_visible_para(self.kwargs['pk'], self.request.user)

    def form_valid(self, form):
        try:
            services.actualizar_grupo(self.object, **form.cleaned_data)
        except CodigoDuplicadoError as exc:
            form.add_error('codigo', str(exc))
            return self.form_invalid(form)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class GrupoBajaView(PermisoRequeridoMixin, HtmxTriggerMixin, TituloContextMixin, DeleteView):
    permiso_requerido = 'groups.manage'
    template_name = 'crud/confirm_delete_modal.html'
    success_url = reverse_lazy('organizacion:grupo-list')
    titulo = 'Desactivar grupo'

    def get_object(self, queryset=None):
        return services.obtener_grupo_visible_para(self.kwargs['pk'], self.request.user)

    def form_valid(self, form):
        services.desactivar_grupo(self.object)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class GrupoReactivarView(PermisoRequeridoMixin, HtmxTriggerMixin, View):
    permiso_requerido = 'groups.manage'

    def post(self, request, pk):
        grupo = services.obtener_grupo_visible_para(pk, request.user)
        services.reactivar_grupo(grupo)
        messages.success(request, f'Grupo «{grupo.nombre}» reactivado.')
        return self._respuesta_htmx() or HttpResponseRedirect(
            reverse_lazy('organizacion:grupo-list'),
        )


# --- Especialidad -------------------------------------------------------------
# catálogo global: requiere "specialties.view"/"specialties.manage" (GROUP_ADMIN, CLINIC_ADMIN).


class EspecialidadListView(PermisoRequeridoMixin, ListaFiltradaMixin, SingleTableMixin, FilterView):
    permiso_requerido = 'specialties.view'
    table_class = EspecialidadTable
    filterset_class = EspecialidadFilter
    template_name = 'crud/list.html'
    paginate_by = 20
    titulo = 'Especialidades'
    url_crear_name = 'organizacion:especialidad-crear'

    def get_queryset(self):
        return services.listar_especialidades()


class EspecialidadDetalleView(PermisoRequeridoMixin, DetailView):
    permiso_requerido = 'specialties.view'
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
    PermisoRequeridoMixin,
    HtmxTriggerMixin,
    TituloContextMixin,
    CreateView,
):
    permiso_requerido = 'specialties.manage'
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
    PermisoRequeridoMixin,
    HtmxTriggerMixin,
    TituloContextMixin,
    UpdateView,
):
    permiso_requerido = 'specialties.manage'
    form_class = EspecialidadForm
    template_name = 'crud/form_modal.html'
    success_url = reverse_lazy('organizacion:especialidad-list')
    titulo = 'Editar especialidad'

    def get_object(self, queryset=None):
        return services.obtener_especialidad(self.kwargs['pk'])

    def form_valid(self, form):
        services.actualizar_especialidad(self.object, **form.cleaned_data)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class EspecialidadBajaView(PermisoRequeridoMixin, HtmxTriggerMixin, TituloContextMixin, DeleteView):
    permiso_requerido = 'specialties.manage'
    template_name = 'crud/confirm_delete_modal.html'
    success_url = reverse_lazy('organizacion:especialidad-list')
    titulo = 'Desactivar especialidad'

    def get_object(self, queryset=None):
        return services.obtener_especialidad(self.kwargs['pk'])

    def form_valid(self, form):
        services.desactivar_especialidad(self.object)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class EspecialidadReactivarView(PermisoRequeridoMixin, HtmxTriggerMixin, View):
    permiso_requerido = 'specialties.manage'

    def post(self, request, pk):
        especialidad = services.obtener_especialidad(pk)
        services.reactivar_especialidad(especialidad)
        messages.success(request, f'Especialidad «{especialidad.nombre}» reactivada.')
        return self._respuesta_htmx() or HttpResponseRedirect(
            reverse_lazy('organizacion:especialidad-list'),
        )


# --- Clinica -------------------------------------------------------------
# superusuario ve todas; GROUP_ADMIN las de su grupo; CLINIC_ADMIN solo las que tiene
# asignadas (ver services.listar_clinicas_visibles_para). create/update usan página completa
# (crud/form_page.html): el formulario incluye 7 campos + m2m especialidades, demasiado para
# un modal cómodo.


class ClinicaListView(PermisoRequeridoMixin, ListaFiltradaMixin, SingleTableMixin, FilterView):
    permiso_requerido = 'clinics.view'
    table_class = ClinicaTable
    filterset_class = ClinicaFilter
    template_name = 'crud/list.html'
    paginate_by = 20
    titulo = 'Clínicas'
    url_crear_name = 'organizacion:clinica-crear'
    crear_en_pagina_completa = True

    def get_queryset(self):
        return services.listar_clinicas_visibles_para(self.request.user)


class ClinicaDetalleView(PermisoRequeridoMixin, DetailView):
    permiso_requerido = 'clinics.view'
    template_name = 'crud/detail_modal.html'
    context_object_name = 'objeto'
    titulo = 'Detalle de la clínica'

    def get_object(self, queryset=None):
        return services.obtener_clinica_visible_para(self.kwargs['pk'], self.request.user)

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


class ClinicaCreateView(PermisoRequeridoMixin, TituloContextMixin, CreateView):
    permiso_requerido = 'clinics.manage'
    form_class = ClinicaForm
    template_name = 'crud/form_page.html'
    success_url = reverse_lazy('organizacion:clinica-list')
    titulo = 'Nueva clínica'
    url_cancelar_name = 'organizacion:clinica-list'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            self.object = services.crear_clinica(**form.cleaned_data)
        except CodigoDuplicadoError as exc:
            form.add_error('codigo', str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'Clínica «{self.object.nombre}» creada.')
        return HttpResponseRedirect(self.get_success_url())


class ClinicaUpdateView(PermisoRequeridoMixin, TituloContextMixin, UpdateView):
    permiso_requerido = 'clinics.manage'
    form_class = ClinicaForm
    template_name = 'crud/form_page.html'
    success_url = reverse_lazy('organizacion:clinica-list')
    titulo = 'Editar clínica'
    url_cancelar_name = 'organizacion:clinica-list'

    def get_object(self, queryset=None):
        return services.obtener_clinica_visible_para(self.kwargs['pk'], self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            services.actualizar_clinica(self.object, **form.cleaned_data)
        except CodigoDuplicadoError as exc:
            form.add_error('codigo', str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'Clínica «{self.object.nombre}» actualizada.')
        return HttpResponseRedirect(self.get_success_url())


class ClinicaBajaView(PermisoRequeridoMixin, HtmxTriggerMixin, TituloContextMixin, DeleteView):
    permiso_requerido = 'clinics.manage'
    template_name = 'crud/confirm_delete_modal.html'
    success_url = reverse_lazy('organizacion:clinica-list')
    titulo = 'Desactivar clínica'

    def get_object(self, queryset=None):
        return services.obtener_clinica_visible_para(self.kwargs['pk'], self.request.user)

    def form_valid(self, form):
        services.desactivar_clinica(self.object)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class ClinicaReactivarView(PermisoRequeridoMixin, HtmxTriggerMixin, View):
    permiso_requerido = 'clinics.manage'

    def post(self, request, pk):
        clinica = services.obtener_clinica_visible_para(pk, request.user)
        services.reactivar_clinica(clinica)
        messages.success(request, f'Clínica «{clinica.nombre}» reactivada.')
        return self._respuesta_htmx() or HttpResponseRedirect(
            reverse_lazy('organizacion:clinica-list'),
        )
