FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build


FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/data ./data
COPY --from=frontend /frontend/dist ./static
ENV STATIC_DIR=/app/static

# The database lives in /app/db, the Fly volume (see fly.toml). It stays
# root-owned from earlier deploys, so the app keeps running as root.
EXPOSE 8080

# Create or migrate the database and import new works, then serve the API and
# the frontend from one process: if it dies, the machine stops and Fly restarts it.
CMD ["sh", "-c", "python -m app.bootstrap && exec uvicorn app.main:app --host 0.0.0.0 --port 8080"]
