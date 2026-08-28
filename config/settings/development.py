"""configuración para entorno de desarrollo."""
from .base import *  # noqa: F401,F403
from .base import BASE_DIR, INSTALLED_APPS, MIDDLEWARE

DEBUG = True
AUTH_PASSWORD_VALIDATORS = []

# sqlite3 para desarrollo local (sin docker) y para la suite de tests: rápido, sin
# dependencias externas. producción usa postgresql (ver production.py).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
}

INSTALLED_APPS = INSTALLED_APPS + [
    'django_extensions',
    'debug_toolbar',
]

MIDDLEWARE = MIDDLEWARE + [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = ['127.0.0.1']
