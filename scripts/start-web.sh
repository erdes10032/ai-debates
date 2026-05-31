#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py setup_render_site
python manage.py collectstatic --noinput

exec daphne \
    -b 0.0.0.0 \
    -p "${PORT:-8000}" \
    config.asgi:application
