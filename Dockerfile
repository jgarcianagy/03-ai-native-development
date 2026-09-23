# --- Stage 1: build the frontend static files ---
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY _frontend/ ./
RUN node build.mjs

# --- Stage 2: Python image running the backend, which also serves the frontend ---
FROM python:3.12-slim
# The frontend is served from the same origin as the API, so CORS is off.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIR=/app/static \
    SDIP_CORS_ORIGINS="" \
    SDIP_DATABASE_URL=sqlite:////data/sdip.db
WORKDIR /app

# Runtime dependencies only, at the versions pinned in requirements.txt.
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=frontend /frontend/dist ./static

RUN useradd --system --uid 10001 --no-create-home crm && \
    mkdir -p /data && chown crm /data
VOLUME /data
USER crm

# Cloud Run injects the port to listen on via $PORT; default to 8000 elsewhere.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
