#!/bin/sh
# arranque del contenedor django en producción: migra, recolecta estáticos (whitenoise los
# sirve luego sin necesidad de nginx delante) y lanza gunicorn.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
