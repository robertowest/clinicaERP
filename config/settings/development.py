"""configuración para entorno de desarrollo."""
from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE

DEBUG = True
AUTH_PASSWORD_VALIDATORS = []

INSTALLED_APPS = INSTALLED_APPS + [
    'django_extensions',
    'debug_toolbar',
]

MIDDLEWARE = MIDDLEWARE + [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = ['127.0.0.1']
