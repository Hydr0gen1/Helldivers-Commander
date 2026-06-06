#!/bin/sh
set -e

if [ -n "${DATABASE_URL:-}" ]; then
  echo "Running database migrations..."
  alembic upgrade head
else
  echo "DATABASE_URL is unset; skipping database migrations and running without persistence."
fi

exec "$@"
