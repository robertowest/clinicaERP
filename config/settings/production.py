"""configuración para entorno de producción (docker compose / despliegue real)."""
from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE as BASE_MIDDLEWARE
from .base import env

DEBUG = False

# postgresql vía variables de entorno (prompt.md §21): nunca credenciales en settings.py.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST', default='localhost'),
        'PORT': env('POSTGRES_PORT', default='5432'),
    },
}

# con DEBUG=False el shim de estáticos de `runserver` no sirve nada, y gunicorn tampoco:
# whitenoise los sirve directamente desde la app sin necesitar un nginx delante.
MIDDLEWARE = [BASE_MIDDLEWARE[0], 'whitenoise.middleware.WhiteNoiseMiddleware', *BASE_MIDDLEWARE[1:]]

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
