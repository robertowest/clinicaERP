# FORMULARIO.md

Guía de las dos variantes de formulario del patrón CRUD reutilizable (`templates/crud/`): **modal** (Bootstrap5 + htmx, sin recarga de página) y **página completa** (formulario largo/complejo).

Documentación de qué hay que tocar, configurar y definir para dar de alta una entidad nueva con cada una, y las dos "trampas" de herencia de atributos htmx ya detectadas y corregidas en el proyecto.

Ejemplos reales ya implementados: `Grupo`/`Especialidad` (`apps/organizacion`) usan modal; `Clinica` (`apps/organizacion`) y `Usuario` (`apps/usuarios`) usan página completa.

## 1. Cuándo usar cada una

| | Modal | Página completa |
|---|---|---|
| Cuándo | Formulario corto (pocos campos, sin widgets complejos) | Formulario largo o con widgets complejos (ej. `SelectMultiple` de m2m) |
| Template crear/editar | `crud/form_modal.html` | `crud/form_page.html` |
| Ejemplo en el repo | `GrupoForm`, `EspecialidadForm` | `ClinicaForm` (m2m `especialidades`), `UsuarioCreateForm` (muchos campos) |
| Ver / Baja / Reactivar | Siempre modal, en ambos casos (`detail_modal.html`, `confirm_delete_modal.html`) | igual |

La elección es **por entidad**, no global: cada app decide crear/editar en modal o en página completa según la complejidad de su formulario; el resto de acciones (Ver, Desactivar, Reactivar) siempre son modales, se elija lo que se elija para crear/editar.

## 2. Piezas comunes (no cambian entre variantes)

- `templates/base.html`: contenedor fijo `#modal-crud` / `#modal-crud-content` (una sola vez por página, cargado siempre).
- `static/js/app.js`: orquesta la apertura del modal (`htmx:afterSwap` sobre `#modal-crud-content`) y su cierre (evento `modal-cerrar` disparado por el servidor vía cabecera `HX-Trigger`). No se toca al añadir una app nueva.
- `templates/crud/detail_modal.html` (Ver) y `templates/crud/confirm_delete_modal.html` (Desactivar): siempre modales, independientemente de la variante elegida para crear/editar.
- `apps/core/mixins.py`:

  - `StaffRequiredMixin` — restringe la vista a `is_staff` (o a `LoginRequiredMixin` a secas si es solo lectura para cualquier autenticado).
  - `HtmxTriggerMixin` — responde 204 + `HX-Trigger: refrescar-lista, modal-cerrar` cuando la petición viene de htmx; si no, redirige normalmente. **Solo se usa en la variante modal** y siempre en Baja/Reactivar, en ambas variantes.
  - `ListaFiltradaMixin` — contexto común de `crud/list.html` (`titulo`, `url_crear`, `crear_en_pagina_completa`).
  - `TituloContextMixin` — contexto común de formularios/confirmaciones (`titulo`, `url_cancelar` si se define `url_cancelar_name`).
- `apps/<app>/forms.py`: en **ambas** variantes el `ModelForm` lleva:
  ```python
  self.helper = FormHelper(self)
  self.helper.form_tag = False
  ```
  El `<form>` HTML lo pone siempre la plantilla (`form_modal.html`/`form_page.html`), nunca crispy — por eso `forms.py` es idéntico se elija la variante que se elija.

## 3. Opción A — Formulario en modal

Ejemplo de referencia: `GrupoCreateView`/`GrupoUpdateView` en `apps/organizacion/views.py` + `GrupoTable` en `apps/organizacion/tables.py`.

1. **`tables.py`**: la columna `acciones` (`TemplateColumn` con `template_name='crud/_acciones_columna.html'`) **no** incluye `edicion_pagina_completa` en `extra_context` (o lo pone a `False`, que es el valor por defecto si no se indica).

2. **`views.py`**:
   ```python
   class XCreateView(StaffRequiredMixin, HtmxTriggerMixin, TituloContextMixin, CreateView):
       form_class = XForm
       template_name = 'crud/form_modal.html'
       success_url = reverse_lazy('app:x-list')
       titulo = 'Nuevo x'

       def form_valid(self, form):
           try:
               self.object = services.crear_x(**form.cleaned_data)
           except CodigoDuplicadoError as exc:
               form.add_error('campo', str(exc))
               return self.form_invalid(form)
           return self._respuesta_htmx() or HttpResponseRedirect(self.get_success_url())
   ```
   `XUpdateView` es análoga (`get_object` + `services.actualizar_x`). Ambas heredan `HtmxTriggerMixin` y usan `crud/form_modal.html`.

3. **`urls.py`**: rutas estándar `x-crear`, `x-detalle`, `x-editar`, `x-eliminar`, `x-reactivar` (sin diferencia respecto a la opción B).

4. **`_acciones_columna.html`** (compartido por toda la app; ya contempla esta rama, no hace falta tocarlo salvo que se añada una acción nueva): el botón "Editar" de la rama `{% else %}` (`edicion_pagina_completa` falso) es:

   ```html
   <button type="button"
           hx-get="{% url url_prefix|add:'-editar' record.pk %}"
           hx-target="#modal-crud-content"
           hx-select="unset" hx-swap="unset" hx-push-url="unset">
   ```
   Los tres atributos `="unset"` son **obligatorios** en cualquier botón nuevo que abra el modal.

5. **`list.html`**: no se toca — el botón "Nuevo" ya se renderiza como `hx-get` automáticamente cuando `crear_en_pagina_completa` es `False`.

## 4. Opción B — Formulario en página completa

Ejemplo de referencia: `ClinicaCreateView`/`ClinicaUpdateView` en `apps/organizacion/views.py` + `ClinicaTable`; también `UsuarioCreateView`/`UsuarioUpdateView` en `apps/usuarios`.

1. **`tables.py`**: la columna `acciones` añade `'edicion_pagina_completa': True` a `extra_context`.

2. **`views.py`**:

   ```python
   class XCreateView(StaffRequiredMixin, TituloContextMixin, CreateView):
       form_class = XForm
       template_name = 'crud/form_page.html'
       success_url = reverse_lazy('app:x-list')
       titulo = 'Nuevo x'
       url_cancelar_name = 'app:x-list'

       def form_valid(self, form):
           try:
               self.object = services.crear_x(**form.cleaned_data)
           except CodigoDuplicadoError as exc:
               form.add_error('campo', str(exc))
               return self.form_invalid(form)
           messages.success(self.request, f'X «{self.object}» creado.')
           return HttpResponseRedirect(self.get_success_url())
   ```
   Diferencias clave frente a la opción A: **no** lleva `HtmxTriggerMixin`, sí `url_cancelar_name` (lo usa `crud/form_page.html` para el botón "Cancelar"), y
   `form_valid` termina siempre en un `HttpResponseRedirect` normal (nunca `_respuesta_htmx()`, porque no hay modal que cerrar).

3. **`urls.py`**: exactamente igual que en la opción A.

4. **`_acciones_columna.html`**: el botón "Editar" de la rama `{% if edicion_pagina_completa %}` es un enlace normal:

   ```html
   <a class="btn btn-sm btn-outline-secondary" title="Editar" hx-boost="false" href="{% url url_prefix|add:'-editar' record.pk %}">
   ```
   `hx-boost="false"` es **obligatorio**.

5. **`list.html`**: no se toca — el botón "Nuevo" ya se renderiza como `<a href>` normal cuando `crear_en_pagina_completa` es `True`. Ese enlace vive fuera de `#lista-wrapper`, así que no necesita `hx-boost="false"` (no hereda nada de él).

## 5. Troubleshooting: herencia de atributos htmx

`#lista-wrapper` en `crud/list.html` declara `hx-boost="true" hx-target="#tabla-container" hx-select="#tabla-container" hx-swap="outerHTML" hx-push-url="true"`.
**htmx** hereda estos atributos a todo elemento descendiente que no los sobrescriba. Estos son dos *bugs* que ya ocurrieron y fueron corregidos (para tenerlo en cuenta):

**Bug 1 — botones de modal que se quedaban vacíos o dejaban de abrirse.**
Un botón `hx-get` dentro de `#tabla-container` que solo sobrescribe `hx-target` sigue heredando `hx-select="#tabla-container"` y `hx-swap="outerHTML"`. La respuesta del modal (`form_modal.html`, `detail_modal.html`...) no contiene ningún elemento `#tabla-container`, así que htmx selecciona un fragmento vacío y el `outerHTML` swap borra `#modal-crud-content` del DOM en vez de rellenarlo.
**Solución**: todo botón que abra el modal lleva `hx-select="unset" hx-swap="unset" hx-push-url="unset"`.

**Bug 2 — enlaces "Editar"/similares de página completa que no navegaban.**
Un `<a href="...">` normal dentro de `#tabla-container` hereda `hx-boost="true"`, así que htmx intercepta el clic como si fuera una navegación boosteada y aplica el mismo `hx-select="#tabla-container"` sobre la respuesta — que es una página completamente distinta (`form_page.html`) sin ese elemento. Resultado: fragmento vacío, `#tabla-container` se borra y la página de destino nunca se pinta, aunque visitar la URL directamente funcione perfecto (ahí no interviene htmx).
**Solución**: todo enlace de este tipo lleva `hx-boost="false"`.

**Regla general** al añadir cualquier botón/enlace nuevo dentro de `#tabla-container` que no deba comportarse como "recargar la lista": revisar qué atributos hereda de `#lista-wrapper` y neutralizarlos explícitamente (`="unset"` para atributos htmx, `hx-boost="false"` si es un `<a>` de navegación normal).

## 6. Checklist rápida

**Modal** (crear entidad nueva con formulario corto):
- [ ] `forms.py`: `ModelForm` con `FormHelper(form_tag=False)`.
- [ ] `tables.py`: `acciones` sin `edicion_pagina_completa` (o `False`).
- [ ] `views.py`: `XCreateView`/`XUpdateView` con `HtmxTriggerMixin` + `template_name='crud/form_modal.html'`.
- [ ] `views.py`: `XDetalleView` (`crud/detail_modal.html`), `XBajaView` (`crud/confirm_delete_modal.html`, con `HtmxTriggerMixin`), `XReactivarView`.
- [ ] `urls.py`: `x-crear`, `x-detalle`, `x-editar`, `x-eliminar`, `x-reactivar`.
- [ ] Confirmar que los botones de `_acciones_columna.html` llevan `hx-select="unset" hx-swap="unset" hx-push-url="unset"`.

**Página completa** (crear entidad nueva con formulario largo/complejo):

- [ ] `forms.py`: `ModelForm` con `FormHelper(form_tag=False)` (igual que en modal).
- [ ] `tables.py`: `acciones` con `'edicion_pagina_completa': True`.
- [ ] `views.py`: `XCreateView`/`XUpdateView` **sin** `HtmxTriggerMixin`, `template_name='crud/form_page.html'`, `url_cancelar_name` definido, `form_valid` termina en `HttpResponseRedirect` + `messages.success`.
- [ ] `views.py`: `XDetalleView`, `XBajaView`, `XReactivarView` — igual que en modal (siempre modales).
- [ ] `urls.py`: igual que en modal.
- [ ] Confirmar que el enlace "Editar" de `_acciones_columna.html` lleva `hx-boost="false"`.





---

cambios a realizar

```text
# tables.py - MODAL
class UsuarioTable(tables.Table):
    ...
    acciones = tables.TemplateColumn(
        template_name='crud/_acciones_columna.html',
        orderable=False,
        verbose_name='',
        extra_context={
            'url_prefix': 'usuarios:usuario',
            'edicion_pagina_completa': True,            # NO MODAL: 'edicion_pagina_completa': False,
            'mostrar_gestion_accesos': True,
        },
    )


# views.py - MODAL con HtmxTriggerMixin - NO MODAL sin HtmxTriggerMixin
class UsuarioListView(StaffRequiredMixin, HtmxTriggerMixin, TituloContextMixin, CreateView):
    table_class = UsuarioTable
    filterset_class = UsuarioFilter
    template_name = 'crud/list.html'
    paginate_by = 20
    titulo = 'Usuarios'
    url_crear_name = 'usuarios:usuario-crear'
    crear_en_pagina_completa = True                     # NO MODAL: crear_en_pagina_completa = False

    def get_queryset(self):
        return services.listar_usuarios()

class UsuarioCreateView(StaffRequiredMixin, TituloContextMixin, CreateView):
    template_name = 'crud/form_modal.html'              # NO MODAL: crud/form_page.html

class UsuarioUpdateView(StaffRequiredMixin, TituloContextMixin, UpdateView):
    template_name = 'crud/form_modal.html'              # NO MODAL: crud/form_page.html
``
