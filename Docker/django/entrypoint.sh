#!/bin/sh
set -e

# Use venv (in case PATH wasn't applied for some reason)
export PATH="/app/.venv/bin:$PATH"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"