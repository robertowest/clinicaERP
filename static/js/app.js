/* comportamiento genérico del modal crud (bootstrap5 + htmx) y del sidebar responsive.
 * las plantillas de templates/crud/ solo declaran atributos hx-*; toda la orquestación
 * del modal vive aquí, en un único sitio, para no repetirla por cada app.
 */
(function () {
    'use strict';

    var modalEl = document.getElementById('modal-crud');
    if (!modalEl) return;

    var modal = new bootstrap.Modal(modalEl);

    // cualquier hx-get/hx-post cuyo hx-target sea #modal-crud-content abre el modal
    // al recibir contenido (crear/editar/ver/confirmar baja).
    document.body.addEventListener('htmx:afterSwap', function (evento) {
        if (evento.detail.target && evento.detail.target.id === 'modal-crud-content') {
            modal.show();
        }
    });

    // el servidor dispara "modal-cerrar" (cabecera HX-Trigger) tras un guardado/baja
    // exitosos; "refrescar-lista" lo escucha el contenedor de la tabla en crud/list.html.
    document.body.addEventListener('modal-cerrar', function () {
        modal.hide();
    });

    // limpiamos el contenido al cerrar para no mostrar el formulario anterior un
    // instante antes de que llegue el nuevo swap.
    modalEl.addEventListener('hidden.bs.modal', function () {
        document.getElementById('modal-crud-content').innerHTML = '';
    });

    // los formularios de templates/crud/ ya llevan {% csrf_token %}, pero los botones de
    // acción rápida (reactivar) hacen hx-post directo sin <form>: añadimos la cabecera
    // csrf a toda petición htmx leyendo la cookie que django ya deja en el navegador.
    document.body.addEventListener('htmx:configRequest', function (evento) {
        evento.detail.headers['X-CSRFToken'] = obtenerCookie('csrftoken');
    });

    function obtenerCookie(nombre) {
        var match = document.cookie.match('(^|;)\\s*' + nombre + '\\s*=\\s*([^;]+)');
        return match ? match.pop() : '';
    }

    var toggleSidebar = document.getElementById('erp-toggle-sidebar');
    var sidebar = document.querySelector('.erp-sidebar');
    if (toggleSidebar && sidebar) {
        toggleSidebar.addEventListener('click', function () {
            sidebar.classList.toggle('mostrar');
        });
    }
})();
