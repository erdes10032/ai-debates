#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py setup_render_site

exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
