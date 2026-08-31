# ERP Clínica — Backend

Backend de un ERP clínico multi-sede: gestión de grupos empresariales, clínicas, usuarios con roles por clínica, pacientes y médicos, con aislamiento estricto de datos entre grupos (multi-tenant). 
API REST (DRF + JWT) y UI server-rendered (HTMX + Bootstrap5) sobre los mismos modelos y la misma capa de servicios.

## Arquitectura

- **Stack**: Django 5, Django REST Framework, PostgreSQL (producción) / SQLite (desarrollo local y tests), `djangorestframework-simplejwt`, `django-filter`, `django-tables2`, `django-crispy-forms` + `crispy-bootstrap5`, HTMX, `drf-spectacular`, `django-cors-headers`.
- **Multi-tenant por `grupo_id`** (shared database, sin BD por tenant): ninguna consulta puede cruzar grupos, ni por queryset ni por id directo. El aislamiento se resuelve una única vez por app en `services.py`  (`listar_X_visibles_para`/`obtener_X_visible_para`), nunca repitiendo `filter(grupo=...)` en vistas o serializers.
- **Apps**: `core` (modelos base, sin lógica de negocio), `organizacion` (Grupo, Clínica, Especialidad), `usuarios` (`CustomUser`, roles sobre `Group`/`Permission` de Django, JWT), `pacientes`, `medicos` (Médico + especialidad por clínica).
- **Toda la lógica de negocio vive en `services.py`** de cada app: vistas, viewsets, serializers, filtros y tablas nunca acceden al ORM directamente (excepción: `admin.py`).

## Requisitos

- Docker + Docker Compose (recomendado), **o**
- Python 3.12, `pip`, y un entorno virtual, para ejecución local sin Docker (usa SQLite).

## Instalación

```bash
git clone <repo>
cd <repo>
cp .env.example .env      # ajustar SECRET_KEY y credenciales si hace falta
```

### Con Docker (recomendado)

```bash
docker compose up --build
```

Levanta PostgreSQL + el backend (gunicorn, `config.settings.production`), aplicando migraciones y `collectstatic` automáticamente en el arranque (ver `docker-entrypoint.sh`).
Accesible en `http://localhost:8000`.

### En local sin Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py runserver
```

Usa `config.settings.development` (SQLite, `DEBUG=True`) por defecto — no requiere PostgreSQL levantado.

## Variables de entorno

Definidas en `.env` (nunca se versiona; ver `.env.example`):

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | clave secreta de Django. |
| `DEBUG` | `True`/`False` (en `docker compose`, `config.settings.production` la fuerza a `False` sin importar esta variable). |
| `ALLOWED_HOSTS` | hosts separados por coma. |
| `DJANGO_SETTINGS_MODULE` | módulo de settings para ejecución **local sin Docker**; `docker compose` lo sobrescribe siempre a `config.settings.production` (ver `docker-compose.yml`). |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT` | credenciales de PostgreSQL, usadas solo por `config.settings.production`. |
| `POSTGRES_HOST` | host de PostgreSQL; `docker compose` lo sobrescribe a `db` (nombre del servicio). |
| `CORS_ALLOWED_ORIGINS` | orígenes permitidos para CORS, separados por coma (nunca `CORS_ALLOW_ALL_ORIGINS=True` en producción). |

## Docker

```text
Dockerfile            # imagen de la app: gunicorn + whitenoise (estáticos), usuario no-root
docker-compose.yml     # servicios "db" (postgres:16, sin publicar puerto al host) y "django"
docker-entrypoint.sh   # migrate → collectstatic → gunicorn
```

```bash
docker compose up --build          # arranque
docker compose exec django python manage.py seed             # datos de demo
docker compose exec django python manage.py createsuperuser  # superusuario propio
docker compose down                # detener (añadir -v para borrar también el volumen de datos)
```

## Migraciones

```bash
python manage.py makemigrations   # tras cambiar modelos
python manage.py migrate          # aplicarlas (automático al arrancar en Docker)
```

## Creación de superusuario

```bash
python manage.py createsuperuser
# o, dentro de docker:
docker compose exec django python manage.py createsuperuser
```

## Datos de demo

```bash
python manage.py seed
```

Comando idempotente (se puede ejecutar varias veces sin duplicar datos). Crea:

- Superusuario `superadmin`.
- Grupo **Atenea** con sus clínicas (Aldaia, Torrent, Eliana) y el catálogo de especialidades.
- Usuarios de demo con roles (`atenea.admin` GROUP_ADMIN, `atenea.aldaia.admin` CLINIC_ADMIN, `atenea.aldaia.doctor`/`atenea.eliana.doctor` DOCTOR, `atenea.recepcion` RECEPTIONIST en dos clínicas).
- Médicos (ligados a los usuarios `DOCTOR`, con especialidad asignada por clínica) y varios pacientes de ejemplo.

**Contraseña de todos los usuarios de demo (incluido `superadmin`): `DemoClinica2026`.**

## Ejecución

- Docker: `docker compose up --build` → `http://localhost:8000`.
- Local: `python manage.py migrate && python manage.py seed && python manage.py runserver`.

Acceso: `/admin/`, `/api/v1/`, `/api/docs/` (Swagger UI), `/api/redoc/`, `/api/schema/` (OpenAPI JSON).

## Tests

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

Incluye tests por app (modelos, servicios, API, vistas HTML) y tests de integración cross-app en `tests/` (aislamiento multi-tenant de punta a punta vía JWT real, smoke test de infraestructura). El aislamiento multi-tenant —que un usuario del Grupo A no pueda leer ni resolver por id directo un recurso del Grupo B— está cubierto explícitamente en cada app y en `tests/test_integracion_multi_tenant.py`.

## Endpoints principales

Autenticación JWT (`djangorestframework-simplejwt`):

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/v1/auth/token/` | login, devuelve `access`/`refresh`. |
| `POST` | `/api/v1/auth/token/refresh/` | renueva el `access` token. |
| `GET` | `/api/v1/auth/me/` | usuario autenticado + grupo + clínicas accesibles + roles. |

Recursos (todos requieren JWT salvo indicación contraria; permisos granulares por rol):

| Endpoint | Recurso |
|---|---|
| `/api/v1/grupos/` | Grupos empresariales |
| `/api/v1/clinicas/` | Clínicas |
| `/api/v1/especialidades/` | Especialidades médicas |
| `/api/v1/usuarios/` | Usuarios (solo staff) |
| `/api/v1/pacientes/` | Pacientes |
| `/api/v1/medicos/` | Médicos |

Documentación: `/api/schema/` (OpenAPI JSON), `/api/docs/` (Swagger UI), `/api/redoc/` (ReDoc) — accesibles sin autenticación.

### Ejemplos `curl`

```bash
# login
curl -s -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "atenea.admin", "password": "DemoClinica2026"}'
# → {"refresh": "...", "access": "..."}

TOKEN="<pegar el access de arriba>"

# usuario autenticado + grupo + clínicas + roles
curl -s http://localhost:8000/api/v1/auth/me/ \
  -H "Authorization: Bearer $TOKEN"

# listar pacientes del propio grupo (aislamiento automático por usuario autenticado)
curl -s http://localhost:8000/api/v1/pacientes/ \
  -H "Authorization: Bearer $TOKEN"

# buscar médicos por colegiado/nombre
curl -s "http://localhost:8000/api/v1/medicos/?search=Cardio" \
  -H "Authorization: Bearer $TOKEN"

# crear un paciente (el campo "grupo" se asigna automáticamente al del usuario autenticado)
curl -s -X POST http://localhost:8000/api/v1/pacientes/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nhc": "NHC9999", "nombre": "Test", "apellido": "Paciente", "documento_tipo": "dni",
       "documento_numero": "99999999Z", "fecha_nacimiento": "1990-01-01", "sexo": "M"}'
```
