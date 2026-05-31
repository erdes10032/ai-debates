#!/bin/sh
set -e

python manage.py migrate --noinput

python manage.py shell -c "
import os
from django.contrib.auth import get_user_model

User = get_user_model()

username = os.getenv('ADMIN_USERNAME')
email = os.getenv('ADMIN_EMAIL')
password = os.getenv('ADMIN_PASSWORD')

if username and email and password:
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        print('Superuser created')
    else:
        print('Superuser already exists')
else:
    print('Admin environment variables not set')
"

python manage.py setup_render_site
python manage.py collectstatic --noinput

exec daphne \
    -b 0.0.0.0 \
    -p "${PORT:-8000}" \
    config.asgi:application