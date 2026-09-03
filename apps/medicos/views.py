"""vistas html/htmx de medicos y ausencias: listado (django-tables2 + django-filter),
formulario en modal (ausencias) o página completa (médicos), detalle/baja en modal
bootstrap, y gestión de especialidad por clínica en página propia (clon del patrón
`UsuarioAccesosView` de apps.usuarios). todo el acceso a datos pasa por services.py.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, TemplateView, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin

from apps.core.mixins import HtmxTriggerMixin, ListaFiltradaMixin, TituloContextMixin
from apps.medicos import services
from apps.medicos.exceptions import (
    ColegiadoDuplicadoError,
    MedicosError,
    UsuarioFueraDeGrupoError,
    UsuarioYaEsMedicoError,
)
from apps.medicos.filters import MedicoAusenciaFilter, MedicoFilter
from apps.medicos.forms import MedicoAusenciaForm, MedicoClinicaForm, MedicoForm
from apps.medicos.tables import MedicoAusenciaTable, MedicoTable
from apps.usuarios.mixins import PermisoRequeridoMixin

# --- Dashboards por rol ------------------------------------------------------


class MedicoDashboardView(LoginRequiredMixin, TemplateView):
    """
    panel del médico (destino post-login de `Roles.DOCTOR`, ver
    `apps.usuarios.services.url_post_login`). solo exige sesión iniciada: no hay todavía
    contenido sensible que proteger con `doctors.view` — cuando se implemente la agenda
    real (`citas`/`agenda`, ver CLAUDE.md §"módulos futuros") esta vista se sustituirá o
    ganará el permiso granular que corresponda.
    """

    template_name = 'medicos/dashboard.html'


# --- Gestión de médicos --------------------------------------------------------
# superusuario ve todos los médicos; el resto ve los de su propio grupo (ver
# services.listar_medicos_visibles_para). permisos granulares por acción: doctors.view
# (list/detalle), doctors.create, doctors.update, doctors.delete (baja/reactivar).


class MedicoListView(PermisoRequeridoMixin, ListaFiltradaMixin, SingleTableMixin, FilterView):
    permiso_requerido = 'doctors.view'
    table_class = MedicoTable
    filterset_class = MedicoFilter
    template_name = 'crud/list.html'
    paginate_by = 20
    titulo = 'Médicos'
    url_crear_name = 'medicos:medico-crear'
    crear_en_pagina_completa = True

    def get_queryset(self):
        return services.listar_medicos_visibles_para(self.request.user)


class MedicoDetalleView(PermisoRequeridoMixin, DetailView):
    permiso_requerido = 'doctors.view'
    template_name = 'crud/detail_modal.html'
    context_object_name = 'objeto'
    titulo = 'Detalle del médico'

    def get_object(self, queryset=None):
        return services.obtener_medico_visible_para(self.kwargs['pk'], self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        medico = context['objeto']
        context['titulo'] = self.titulo
        context['campos'] = [
            ('Grupo', medico.grupo.nombre),
            ('Nombre', medico.nombre_completo),
            ('Correo', medico.email or '—'),
            ('Colegiado', medico.colegiado),
            ('Teléfono', medico.telefono or '—'),
            ('Estado', 'Activo' if medico.is_active else 'Inactivo'),
        ]
        return context


class MedicoCreateView(PermisoRequeridoMixin, TituloContextMixin, CreateView):
    permiso_requerido = 'doctors.create'
    form_class = MedicoForm
    template_name = 'crud/form_page.html'
    success_url = reverse_lazy('medicos:medico-list')
    titulo = 'Nuevo médico'
    url_cancelar_name = 'medicos:medico-list'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs

    def form_valid(self, form):
        datos = dict(form.cleaned_data)
        if 'grupo' not in datos:
            datos['grupo'] = self.request.user.grupo
        try:
            self.object = services.crear_medico(**datos)
        except ColegiadoDuplicadoError as exc:
            form.add_error('colegiado', str(exc))
            return self.form_invalid(form)
        except (UsuarioFueraDeGrupoError, UsuarioYaEsMedicoError) as exc:
            form.add_error('usuario', str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'Médico «{self.object}» creado.')
        return HttpResponseRedirect(self.get_success_url())


class MedicoUpdateView(PermisoRequeridoMixin, TituloContextMixin, UpdateView):
    permiso_requerido = 'doctors.update'
    form_class = MedicoForm
    template_name = 'crud/form_page.html'
    success_url = reverse_lazy('medicos:medico-list')
    titulo = 'Editar médico'
    url_cancelar_name = 'medicos:medico-list'

    def get_object(self, queryset=None):
        return services.obtener_medico_visible_para(self.kwargs['pk'], self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs

    def form_valid(self, form):
        datos = {campo: valor for campo, valor in form.cleaned_data.items() if campo != 'usuario'}
        try:
            services.actualizar_medico(self.object, **datos)
        except ColegiadoDuplicadoError as exc:
            form.add_error('colegiado', str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'Médico «{self.object}» actualizado.')
        return HttpResponseRedirect(self.get_success_url())


class MedicoBajaView(PermisoRequeridoMixin, HtmxTriggerMixin, TituloContextMixin, DeleteView):
    permiso_requerido = 'doctors.delete'
    template_name = 'crud/confirm_delete_modal.html'
    success_url = reverse_lazy('medicos:medico-list')
    titulo = 'Desactivar médico'

    def get_object(self, queryset=None):
        return services.obtener_medico_visible_para(self.kwargs['pk'], self.request.user)

    def form_valid(self, form):
        services.desactivar_medico(self.object)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class MedicoReactivarView(PermisoRequeridoMixin, HtmxTriggerMixin, View):
    permiso_requerido = 'doctors.delete'

    def post(self, request, pk):
        medico = services.obtener_medico_visible_para(pk, request.user)
        services.reactivar_medico(medico)
        messages.success(request, f'Médico «{medico}» reactivado.')
        return self._respuesta_htmx() or HttpResponseRedirect(
            reverse_lazy('medicos:medico-list'),
        )


# --- MedicoClinicaEspecialidad (especialidad por clínica) --------------------
# página propia, no encaja en el patrón crud/list.html: no es un listado paginado con
# filtros, sino la gestión de las pocas asignaciones de un único médico (clon de
# apps.usuarios.views: UsuarioAccesosView/UsuarioAccesoCrearView/UsuarioAccesoEliminarView).


class MedicoClinicasView(PermisoRequeridoMixin, View):
    permiso_requerido = 'doctors.update'
    template_name = 'medicos/clinicas.html'

    def get(self, request, medico_pk):
        medico = services.obtener_medico_visible_para(medico_pk, request.user)
        return render(request, self.template_name, self._contexto_base(medico))

    def _contexto_base(self, medico, form=None):
        return {
            'medico': medico,
            'asignaciones': services.listar_asignaciones_clinica(medico=medico),
            'form': form or MedicoClinicaForm(medico=medico),
        }


class MedicoClinicaCrearView(PermisoRequeridoMixin, View):
    """crea una asignación de especialidad por clínica y devuelve la tabla parcial (htmx) o
    redirige a la página completa si la petición no viene de htmx."""

    permiso_requerido = 'doctors.update'
    partial_template = 'medicos/_clinicas_tabla.html'

    def post(self, request, medico_pk):
        medico = services.obtener_medico_visible_para(medico_pk, request.user)
        form = MedicoClinicaForm(request.POST, medico=medico)
        if form.is_valid():
            try:
                datos = form.cleaned_data
                services.asignar_clinica_especialidad(
                    medico=medico, clinica=datos['clinica'], especialidad=datos['especialidad'],
                )
                messages.success(request, 'Especialidad asignada.')
                form = MedicoClinicaForm(medico=medico)
            except MedicosError as exc:
                form.add_error(None, str(exc))
        return self._responder(request, medico, form)

    def _responder(self, request, medico, form):
        if not getattr(request, 'htmx', False):
            return HttpResponseRedirect(reverse('medicos:medico-clinicas', args=[medico.pk]))
        contexto = {
            'medico': medico,
            'asignaciones': services.listar_asignaciones_clinica(medico=medico),
            'form': form,
        }
        return render(request, self.partial_template, contexto)


class MedicoClinicaEliminarView(PermisoRequeridoMixin, View):
    permiso_requerido = 'doctors.update'
    partial_template = 'medicos/_clinicas_tabla.html'

    def post(self, request, medico_pk, pk):
        medico = services.obtener_medico_visible_para(medico_pk, request.user)
        asignacion = services.obtener_asignacion_clinica(pk, medico=medico)
        services.quitar_asignacion_clinica(asignacion)
        messages.success(request, 'Especialidad quitada.')
        if not getattr(request, 'htmx', False):
            return HttpResponseRedirect(reverse('medicos:medico-clinicas', args=[medico.pk]))
        contexto = {
            'medico': medico, 'asignaciones': services.listar_asignaciones_clinica(medico=medico),
            'form': MedicoClinicaForm(medico=medico),
        }
        return render(request, self.partial_template, contexto)


# --- MedicoAusencia (ausencias) -----------------------------------------------
# CRUD en modal (patrón `form_modal.html` / `detail_modal.html` /
# `confirm_delete_modal.html`): el botón «Nuevo» de la lista abre el modal vía
# hx-get, y las vistas devuelven solo el fragmento HTML del modal. al guardar o
# desactivar, `HtmxTriggerMixin` responde 204 con eventos que cierran el modal
# y refrescan la tabla.


class AusenciaListView(PermisoRequeridoMixin, ListaFiltradaMixin, SingleTableMixin, FilterView):
    permiso_requerido = 'doctors.view'
    table_class = MedicoAusenciaTable
    filterset_class = MedicoAusenciaFilter
    template_name = 'crud/list.html'
    paginate_by = 20
    titulo = 'Ausencias de médicos'
    url_crear_name = 'medicos:ausencia-crear'
    crear_en_pagina_completa = False

    def get_queryset(self):
        return services.listar_ausencias_visibles_para(self.request.user)


class AusenciaDetalleView(PermisoRequeridoMixin, DetailView):
    permiso_requerido = 'doctors.view'
    template_name = 'crud/detail_modal.html'
    context_object_name = 'objeto'
    titulo = 'Detalle de ausencia'

    def get_object(self, queryset=None):
        return services.obtener_ausencia_visible_para(self.kwargs['pk'], self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ausencia = context['objeto']
        context['titulo'] = self.titulo
        context['campos'] = [
            ('Médico', ausencia.medico),
            ('Grupo', ausencia.medico.grupo.nombre),
            ('Fecha inicio', ausencia.fecha_inicio),
            ('Fecha fin', ausencia.fecha_fin),
            ('Motivo', ausencia.get_motivo_display()),
            ('Estado', ausencia.get_estado_display()),
            ('Activo', 'Sí' if ausencia.is_active else 'No'),
        ]
        return context


class AusenciaCreateView(PermisoRequeridoMixin, View):
    """crea una ausencia y cierra el modal (htmx) o redirige (no-htmx)."""

    permiso_requerido = 'doctors.create'
    template_name = 'crud/form_modal.html'
    success_url = reverse_lazy('medicos:ausencia-list')

    def get(self, request):
        form = MedicoAusenciaForm(usuario=request.user)
        return render(request, self.template_name, {
            'form': form, 'titulo': 'Nueva ausencia',
        })

    def post(self, request):
        form = MedicoAusenciaForm(request.POST, usuario=request.user)
        if form.is_valid():
            try:
                services.crear_ausencia(**form.cleaned_data)
                messages.success(request, 'Ausencia creada.')
                return self._respuesta_htmx() or HttpResponseRedirect(self.success_url)
            except MedicosError as exc:
                form.add_error(None, str(exc))
        return render(request, self.template_name, {
            'form': form, 'titulo': 'Nueva ausencia',
        })

    def _respuesta_htmx(self):
        if not getattr(self.request, 'htmx', False):
            return None
        from django.http import HttpResponse
        response = HttpResponse(status=204)
        response['HX-Trigger'] = 'refrescar-lista, modal-cerrar'
        return response


class AusenciaUpdateView(PermisoRequeridoMixin, View):
    """actualiza una ausencia y cierra el modal (htmx) o redirige (no-htmx)."""

    permiso_requerido = 'doctors.update'
    template_name = 'crud/form_modal.html'
    success_url = reverse_lazy('medicos:ausencia-list')

    def get(self, request, pk):
        ausencia = services.obtener_ausencia_visible_para(pk, request.user)
        form = MedicoAusenciaForm(instance=ausencia, usuario=request.user)
        return render(request, self.template_name, {
            'form': form, 'titulo': f'Editar ausencia de {ausencia.medico}',
        })

    def post(self, request, pk):
        ausencia = services.obtener_ausencia_visible_para(pk, request.user)
        form = MedicoAusenciaForm(request.POST, instance=ausencia, usuario=request.user)
        if form.is_valid():
            try:
                services.actualizar_ausencia(ausencia, **form.cleaned_data)
                messages.success(request, 'Ausencia actualizada.')
                return self._respuesta_htmx() or HttpResponseRedirect(self.success_url)
            except MedicosError as exc:
                form.add_error(None, str(exc))
        return render(request, self.template_name, {
            'form': form, 'titulo': f'Editar ausencia de {ausencia.medico}',
        })

    def _respuesta_htmx(self):
        if not getattr(self.request, 'htmx', False):
            return None
        from django.http import HttpResponse
        response = HttpResponse(status=204)
        response['HX-Trigger'] = 'refrescar-lista, modal-cerrar'
        return response


class AusenciaBajaView(PermisoRequeridoMixin, HtmxTriggerMixin, TituloContextMixin, DeleteView):
    permiso_requerido = 'doctors.delete'
    template_name = 'crud/confirm_delete_modal.html'
    success_url = reverse_lazy('medicos:ausencia-list')
    titulo = 'Desactivar ausencia'

    def get_object(self, queryset=None):
        return services.obtener_ausencia_visible_para(self.kwargs['pk'], self.request.user)

    def form_valid(self, form):
        services.desactivar_ausencia(self.object)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class AusenciaReactivarView(PermisoRequeridoMixin, HtmxTriggerMixin, View):
    permiso_requerido = 'doctors.delete'

    def post(self, request, pk):
        ausencia = services.obtener_ausencia_visible_para(pk, request.user)
        services.reactivar_ausencia(ausencia)
        messages.success(request, f'Ausencia de «{ausencia.medico}» reactivada.')
        return self._respuesta_htmx() or HttpResponseRedirect(
            reverse_lazy('medicos:ausencia-list'),
        )
