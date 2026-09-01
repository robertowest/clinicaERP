![imagen](usuarios.png)

El context processor `apps.usuarios.context_processors.usuario_context` ya inyecta `perms` (dict `{codename: True}`) en todas las templates. Usamos directamente `{% if perms.patients.view %}` en el sidebar sin necesidad del template tag `tiene_permiso_o_staff` ni de la variable `permiso_editar`.

### Mapeo de secciones → permisos

| Sección/Enlace            | Permiso                                                      |
| ------------------------- | ------------------------------------------------------------ |
| Organización (contenedor) | perms.groups.view OR perms.clinics.view OR perms.specialties.view |
| → Grupos                  | perms.groups.view                                            |
| → Clínicas                | perms.clinics.view                                           |
| → Especialidades          | perms.specialties.view                                       |
| Pacientes                 | perms.patients.view                                          |
| Médicos                   | perms.doctors.view                                           |
| Usuarios                  | perms.users.manage OR request.user.is_staff                  |

​	

### Estructura del sidebar

```python
{% if perms.groups.view or perms.clinics.view or perms.specialties.view %}
    <div class="nav-section-title">Organización</div>
    <div class="nav flex-column">
        {% if perms.groups.view %}
            <a ... href="{% url 'organizacion:grupo-list' %}">Grupos</a>
        {% endif %}
        {% if perms.clinics.view %}
            <a ... href="{% url 'organizacion:clinica-list' %}">Clínicas</a>
        {% endif %}
        {% if perms.specialties.view %}
            <a ... href="{% url 'organizacion:especialidad-list' %}">Especialidades</a>
        {% endif %}
    </div>
{% endif %}

{% if perms.patients.view %}
    <div class="nav-section-title">Pacientes</div>
    ...pacientes link...
{% endif %}

{% if perms.doctors.view %}
    <div class="nav-section-title">Médicos</div>
    ...médicos link...
{% endif %}

{% if perms.users.manage or request.user.is_staff %}
    <div class="nav-section-title">Accesos</div>
    ...usuarios link...
{% endif %}
```

