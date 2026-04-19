#!/bin/sh
set -e

DB_PATH="/app/db/symphonies.db"

if [ ! -f "$DB_PATH" ]; then
  echo "No DB found on volume. Seeding from image..."
  cp /app/db_seed/symphonies.db "$DB_PATH"
fi

exec gunicorn -k uvicorn.workers.UvicornWorker app.main:app \
  --bind 0.0.0.0:8000 \
  --workers 1