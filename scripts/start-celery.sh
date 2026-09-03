#!/bin/sh
set -e

exec celery -A config worker -l info --concurrency="${CELERY_WORKER_CONCURRENCY:-4}"
