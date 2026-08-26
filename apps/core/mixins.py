"""mixins reutilizables por las vistas crud (ver templates/crud/) de cualquier app."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.urls import reverse


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """restringe una vista a usuarios autenticados con `is_staff` (criterio provisional
    hasta la fase 4 de roles, igual que `IsStaffOrReadOnly`/`IsAdminUser` en la api).

    no hace falta `raise_exception`: `AccessMixin.handle_no_permission` ya distingue
    anónimo (redirige a login) de autenticado-sin-permiso (403), vía
    `self.raise_exception or self.request.user.is_authenticated`.
    """

    def test_func(self):
        return self.request.user.is_staff


class HtmxTriggerMixin:
    """tras crear/editar/eliminar en un modal, si la petición viene de htmx respondemos
    204 sin cuerpo y dos eventos: uno para que la lista se recargue y otro para que el
    modal se cierre; si no viene de htmx (js deshabilitado, acceso directo), redirigimos
    normalmente a `success_url`. las vistas de baja (`DeleteView`) sobreescriben
    `form_valid` para llamar a `services.desactivar_*` en vez de `self.object.delete()`,
    así que no reutilizan este `form_valid`; usan `_respuesta_htmx()` directamente, igual
    que las vistas de reactivación (`View` simple, sin formulario).
    """

    evento_refresco = 'refrescar-lista'

    def form_valid(self, form):
        response = super().form_valid(form)
        return self._respuesta_htmx() or response

    def _respuesta_htmx(self):
        if not getattr(self.request, 'htmx', False):
            return None
        response = HttpResponse(status=204)
        response['HX-Trigger'] = f'{self.evento_refresco}, modal-cerrar'
        return response


class ListaFiltradaMixin:
    """contexto común de `crud/list.html`: título de la página y url del botón «nuevo».

    `crear_en_pagina_completa` distingue si el botón «nuevo» abre un modal (hx-get) o
    navega a una página completa (formulario demasiado complejo para un modal).
    """

    titulo = ''
    url_crear_name = None
    crear_en_pagina_completa = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'titulo': self.titulo,
                'url_crear': reverse(self.url_crear_name) if self.url_crear_name else None,
                'crear_en_pagina_completa': self.crear_en_pagina_completa,
            }
        )
        return context


class TituloContextMixin:
    """contexto común de los formularios (modal o página completa) y confirmaciones de
    baja: título mostrado en la cabecera y, si se define `url_cancelar_name`, la url del
    botón «cancelar» de `crud/form_page.html`.
    """

    titulo = ''
    url_cancelar_name = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = self.titulo
        if self.url_cancelar_name:
            context['url_cancelar'] = reverse(self.url_cancelar_name)
        return context
