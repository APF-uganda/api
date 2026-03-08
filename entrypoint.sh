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
exec gunicorn api.wsgi:application --bind 0.0.0.0:8000 --workers 3
