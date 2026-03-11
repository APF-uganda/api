#!/bin/sh
set -e

# Controls:
# - MIGRATE_ON_START=1 runs migrations at startup (default: 1)
# - MIGRATE_STRICT=1 exits if migrations fail (default: 1)
MIGRATE_ON_START="${MIGRATE_ON_START:-1}"
MIGRATE_STRICT="${MIGRATE_STRICT:-1}"

if [ "$MIGRATE_ON_START" = "1" ]; then
  echo "Applying migrations..."
  if [ "$MIGRATE_STRICT" = "1" ]; then
    python manage.py migrate --noinput
  else
    if ! python manage.py migrate --noinput; then
      echo "WARNING: Migration failed, continuing because MIGRATE_STRICT=0."
    fi
  fi
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
WEB_CONCURRENCY="${WEB_CONCURRENCY:-1}"
GUNICORN_THREADS="${GUNICORN_THREADS:-2}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-180}"
GUNICORN_GRACEFUL_TIMEOUT="${GUNICORN_GRACEFUL_TIMEOUT:-30}"
GUNICORN_KEEPALIVE="${GUNICORN_KEEPALIVE:-5}"
GUNICORN_WORKER_CLASS="${GUNICORN_WORKER_CLASS:-gthread}"
GUNICORN_MAX_REQUESTS="${GUNICORN_MAX_REQUESTS:-1000}"
GUNICORN_MAX_REQUESTS_JITTER="${GUNICORN_MAX_REQUESTS_JITTER:-100}"
GUNICORN_LOG_LEVEL="${GUNICORN_LOG_LEVEL:-info}"

exec gunicorn api.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${WEB_CONCURRENCY}" \
  --threads "${GUNICORN_THREADS}" \
  --worker-class "${GUNICORN_WORKER_CLASS}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT}" \
  --keep-alive "${GUNICORN_KEEPALIVE}" \
  --max-requests "${GUNICORN_MAX_REQUESTS}" \
  --max-requests-jitter "${GUNICORN_MAX_REQUESTS_JITTER}" \
  --worker-tmp-dir /dev/shm \
  --log-level "${GUNICORN_LOG_LEVEL}" \
  --access-logfile - \
  --error-logfile -
