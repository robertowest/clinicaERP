"""vistas html/htmx de medicos: listado (django-tables2 + django-filter), formulario en
página completa (4 campos relacionales/identificativos, mismo criterio que Paciente) +
detalle/baja en modal bootstrap, y gestión de especialidad por clínica en página propia
(clon del patrón `UsuarioAccesosView` de apps.usuarios). todo el acceso a datos pasa por
services.py.
"""

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, View
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
from apps.medicos.filters import MedicoFilter
from apps.medicos.forms import MedicoClinicaForm, MedicoForm
from apps.medicos.tables import MedicoTable
from apps.usuarios.mixins import PermisoRequeridoMixin

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
