#!/bin/sh

if [ ! -f "/app/db/symphonies.db" ]; then
  echo "Seeding database..."
  cp /app/db_seed/symphonies.db /app/db/symphonies.db
fi

# Kill any existing processes holding our ports
echo "Cleaning up old processes..."
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 80/tcp 2>/dev/null || true
sleep 2

echo "Starting gunicorn..."
gunicorn -k uvicorn.workers.UvicornWorker app.main:app \
  --bind 127.0.0.1:8000 \
  --workers 1 \
  --chdir /app &

echo "Waiting for gunicorn..."
sleep 5

echo "Starting nginx..."
exec nginx -g "daemon off;"