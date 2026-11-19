#!/bin/sh
set -e

if [ ! -f "/app/db/symphonies.db" ]; then
  echo "Seeding database..."
  cp /app/db_seed/symphonies.db /app/db/symphonies.db
fi

echo "Running migrations..."
cd /app && alembic upgrade head

echo "Starting the API..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# Wait until the API answers (up to 30 s) instead of sleeping a fixed time.
i=0
until python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" 2>/dev/null; do
  i=$((i + 1))
  if [ "$i" -ge 150 ]; then
    echo "The API did not start within 30 seconds." >&2
    exit 1
  fi
  sleep 0.2
done

echo "Starting nginx..."
exec nginx -g "daemon off;"
