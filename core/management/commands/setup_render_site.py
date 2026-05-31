import os

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    help = (
        'Update django.contrib.sites Site domain '
        'from RENDER_EXTERNAL_HOSTNAME.'
    )

    def handle(self, *args, **options):

        hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')

        if not hostname:
            return

        site = Site.objects.get(pk=1)

        if site.domain == hostname:
            return

        site.domain = hostname
        site.name = 'AI Debates'
        site.save(
            update_fields=[
                'domain',
                'name',
            ],
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Updated Site domain to {hostname}',
            ),
        )
