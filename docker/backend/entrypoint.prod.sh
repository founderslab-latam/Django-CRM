#!/bin/bash
# Production start: prepare the app, then hand the process to gunicorn.
#
# Mirrors docker/backend/entrypoint.sh (dev) but ends in a real WSGI server
# instead of `manage.py runserver`. Every step is safe to repeat on each boot,
# which is what makes "git pull && docker compose up -d --build" a complete
# upgrade: migrations and collectstatic run here, not as a separate step.
set -e

echo "Waiting for PostgreSQL at ${DBHOST}:${DBPORT}..."
tries=0
until python -c "import socket, os
s = socket.socket()
s.settimeout(2)
s.connect((os.environ['DBHOST'], int(os.environ['DBPORT'])))
s.close()" 2>/dev/null; do
    tries=$((tries + 1))
    if [ "$tries" -ge 60 ]; then
        echo "ERROR: PostgreSQL still unreachable after 60s." >&2
        exit 1
    fi
    sleep 1
done
echo "PostgreSQL is up."

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Ensuring the default admin exists..."
python manage.py create_default_admin

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Compiling translation catalogs..."
python manage.py compilemessages

workers="${GUNICORN_WORKERS:-3}"
threads="${GUNICORN_THREADS:-4}"
echo "Starting gunicorn: ${workers} workers x ${threads} threads on :8000"
exec gunicorn crm.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${workers}" \
    --threads "${threads}" \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile -
