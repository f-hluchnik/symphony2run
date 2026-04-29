FROM node:20 AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

# Install nginx
RUN apt-get update && apt-get install -y nginx psmisc && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

# Backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/db/symphonies.db ./db_seed/symphonies.db
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
COPY start.sh ./start.sh
RUN chmod +x start.sh

# Frontend static files
COPY --from=frontend-build /app/dist /usr/share/nginx/html

# Config files
RUN rm /etc/nginx/sites-enabled/default 2>/dev/null || true
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["/app/start.sh"]