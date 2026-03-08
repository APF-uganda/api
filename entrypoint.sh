#!/bin/sh
set -e

MIGRATE_ON_START="${MIGRATE_ON_START:-1}"
MIGRATE_STRICT="${MIGRATE_STRICT:-1}"
COLLECTSTATIC="${COLLECTSTATIC:-1}"

echo "Starting container..."

# Optional DB wait
if [ -n "$DB_HOST" ]; then
  echo "Waiting for database at $DB_HOST:$DB_PORT..."
  until nc -z "$DB_HOST" "$DB_PORT"; do
    sleep 2
  done
fi

if [ "$MIGRATE_ON_START" = "1" ]; then
  echo "Applying migrations..."
  if [ "$MIGRATE_STRICT" = "1" ]; then
    python manage.py migrate --noinput
  else
    if ! python manage.py migrate --noinput; then
      echo "WARNING: Migration failed, continuing..."
    fi
  fi
fi

if [ "$COLLECTSTATIC" = "1" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

echo "Starting Gunicorn..."
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
GUNICORN_THREADS="${GUNICORN_THREADS:-2}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
GUNICORN_GRACEFUL_TIMEOUT="${GUNICORN_GRACEFUL_TIMEOUT:-30}"
GUNICORN_KEEPALIVE="${GUNICORN_KEEPALIVE:-5}"
GUNICORN_WORKER_CLASS="${GUNICORN_WORKER_CLASS:-gthread}"

exec gunicorn api.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "$WEB_CONCURRENCY" \
  --threads "$GUNICORN_THREADS" \
  --worker-class "$GUNICORN_WORKER_CLASS" \
  --timeout "$GUNICORN_TIMEOUT" \
  --graceful-timeout "$GUNICORN_GRACEFUL_TIMEOUT" \
  --keep-alive "$GUNICORN_KEEPALIVE" \
  --access-logfile - \
  --error-logfile -