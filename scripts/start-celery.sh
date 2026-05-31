#!/bin/sh
set -e

exec celery -A config worker \
    -l info \
    --pool=threads \
    --concurrency="${CELERY_WORKER_CONCURRENCY:-4}"
