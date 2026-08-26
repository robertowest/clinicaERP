"""vistas html/htmx de usuarios: listado (django-tables2 + django-filter), formulario
en página completa (varios campos, igual criterio que Clinica) y gestión de accesos por
clínica (alta/baja de `UsuarioClinica`) en una página propia con tabla parcial htmx.
todo el acceso a datos pasa por services.py.
"""

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
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
from apps.usuarios import services
from apps.usuarios.exceptions import UsuarioDuplicadoError, UsuariosError
from apps.usuarios.filters import UsuarioFilter
from apps.usuarios.forms import UsuarioClinicaForm, UsuarioCreateForm, UsuarioForm
from apps.usuarios.tables import UsuarioTable

# --- CustomUser -------------------------------------------------------------
# gestión de usuarios restringida a staff, igual criterio que Grupo en organizacion.


class UsuarioListView(StaffRequiredMixin, ListaFiltradaMixin, SingleTableMixin, FilterView):
    table_class = UsuarioTable
    filterset_class = UsuarioFilter
    template_name = 'crud/list.html'
    paginate_by = 20
    titulo = 'Usuarios'
    url_crear_name = 'usuarios:usuario-crear'
    crear_en_pagina_completa = True

    def get_queryset(self):
        return services.listar_usuarios()


class UsuarioDetalleView(StaffRequiredMixin, DetailView):
    template_name = 'crud/detail_modal.html'
    context_object_name = 'objeto'
    titulo = 'Detalle del usuario'

    def get_object(self, queryset=None):
        return services.obtener_usuario(self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = context['objeto']
        asignaciones = services.listar_asignaciones(usuario=usuario)
        texto_accesos = ', '.join(
            f'{a.get_rol_display()} ({a.clinica or "grupo"})' for a in asignaciones
        )
        context['titulo'] = self.titulo
        context['campos'] = [
            ('Usuario', usuario.username),
            ('Nombre completo', usuario.get_full_name() or '—'),
            ('Correo', usuario.email or '—'),
            ('Grupo', usuario.grupo.nombre if usuario.grupo else '—'),
            ('Accesos', texto_accesos or '—'),
            ('Staff', 'Sí' if usuario.is_staff else 'No'),
            ('Estado', 'Activo' if usuario.is_active else 'Inactivo'),
        ]
        return context


class UsuarioCreateView(StaffRequiredMixin, TituloContextMixin, CreateView):
    form_class = UsuarioCreateForm
    template_name = 'crud/form_page.html'
    success_url = reverse_lazy('usuarios:usuario-list')
    titulo = 'Nuevo usuario'
    url_cancelar_name = 'usuarios:usuario-list'

    def form_valid(self, form):
        datos = form.cleaned_data
        try:
            self.object = services.crear_usuario(
                username=datos['username'], password=datos['password1'], email=datos['email'],
                grupo=datos['grupo'], first_name=datos['first_name'], last_name=datos['last_name'],
                is_staff=datos['is_staff'], is_active=datos['is_active'],
            )
        except UsuarioDuplicadoError as exc:
            form.add_error('username', str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'Usuario «{self.object}» creado.')
        return HttpResponseRedirect(self.get_success_url())


class UsuarioUpdateView(StaffRequiredMixin, TituloContextMixin, UpdateView):
    form_class = UsuarioForm
    template_name = 'crud/form_page.html'
    success_url = reverse_lazy('usuarios:usuario-list')
    titulo = 'Editar usuario'
    url_cancelar_name = 'usuarios:usuario-list'

    def get_object(self, queryset=None):
        return services.obtener_usuario(self.kwargs['pk'])

    def form_valid(self, form):
        try:
            services.actualizar_usuario(self.object, **form.cleaned_data)
        except UsuarioDuplicadoError as exc:
            form.add_error('username', str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'Usuario «{self.object}» actualizado.')
        return HttpResponseRedirect(self.get_success_url())


class UsuarioBajaView(StaffRequiredMixin, HtmxTriggerMixin, TituloContextMixin, DeleteView):
    template_name = 'crud/confirm_delete_modal.html'
    success_url = reverse_lazy('usuarios:usuario-list')
    titulo = 'Desactivar usuario'

    def get_object(self, queryset=None):
        return services.obtener_usuario(self.kwargs['pk'])

    def form_valid(self, form):
        services.desactivar_usuario(self.object)
        return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())


class UsuarioReactivarView(StaffRequiredMixin, HtmxTriggerMixin, View):
    def post(self, request, pk):
        usuario = services.obtener_usuario(pk)
        services.reactivar_usuario(usuario)
        messages.success(request, f'Usuario «{usuario}» reactivado.')
        return self._respuesta_htmx() or HttpResponseRedirect(reverse_lazy('usuarios:usuario-list'))


# --- UsuarioClinica (accesos por clínica) ------------------------------------
# página propia, no encaja en el patrón crud/list.html: no es un listado paginado con
# filtros, sino la gestión de las pocas asignaciones de un único usuario.
# El formulario de alta y la tabla de bajas comparten la misma respuesta parcial htmx.


class UsuarioAccesosView(StaffRequiredMixin, View):
    template_name = 'usuarios/accesos.html'

    def get(self, request, usuario_pk):
        usuario = services.obtener_usuario(usuario_pk)
        contexto = self._contexto_base(usuario)
        return render(request, self.template_name, contexto)

    def _contexto_base(self, usuario, form=None):
        return {
            'usuario': usuario,
            'asignaciones': services.listar_asignaciones(usuario=usuario),
            'form': form or UsuarioClinicaForm(usuario=usuario),
        }


class UsuarioAccesoCrearView(StaffRequiredMixin, View):
    """crea una asignación de rol y devuelve la tabla parcial (htmx) o redirige a la
    página completa de accesos si la petición no viene de htmx."""

    partial_template = 'usuarios/_accesos_tabla.html'

    def post(self, request, usuario_pk):
        usuario = services.obtener_usuario(usuario_pk)
        form = UsuarioClinicaForm(request.POST, usuario=usuario)
        if form.is_valid():
            try:
                datos = form.cleaned_data
                services.asignar_rol(usuario=usuario, rol=datos['rol'], clinica=datos['clinica'])
                messages.success(request, 'Acceso asignado.')
                form = UsuarioClinicaForm(usuario=usuario)
            except UsuariosError as exc:
                form.add_error(None, str(exc))
        return self._responder(request, usuario, form)

    def _responder(self, request, usuario, form):
        if not getattr(request, 'htmx', False):
            return HttpResponseRedirect(reverse('usuarios:usuario-accesos', args=[usuario.pk]))
        contexto = {
            'usuario': usuario,
            'asignaciones': services.listar_asignaciones(usuario=usuario),
            'form': form,
        }
        return render(request, self.partial_template, contexto)


class UsuarioAccesoEliminarView(StaffRequiredMixin, View):
    partial_template = 'usuarios/_accesos_tabla.html'

    def post(self, request, usuario_pk, pk):
        usuario = services.obtener_usuario(usuario_pk)
        asignacion = services.obtener_asignacion(pk, usuario=usuario)
        services.quitar_asignacion(asignacion)
        messages.success(request, 'Acceso eliminado.')
        if not getattr(request, 'htmx', False):
            return HttpResponseRedirect(reverse('usuarios:usuario-accesos', args=[usuario.pk]))
        contexto = {
            'usuario': usuario, 'asignaciones': services.listar_asignaciones(usuario=usuario),
            'form': UsuarioClinicaForm(usuario=usuario),
        }
        return render(request, self.partial_template, contexto)
