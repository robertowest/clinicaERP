#!/usr/bin/env python
"""utilidad de línea de comandos de django para tareas administrativas."""
import os
import sys


def main():
    """punto de entrada de manage.py."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            'no se pudo importar django. ¿está instalado y disponible en tu variable '
            'de entorno pythonpath? ¿olvidaste activar un entorno virtual?'
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
