# Bank Alfa Mortgage AI Demo — single container: FastAPI serves REST + WS + built SPA.

# --- Stage 1: build the React SPA (Vite emits to ../app/static) ---
FROM node:24-alpine AS web
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --- Stage 2: Python runtime ---
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    VOICE_PROVIDER=simulated \
    DOCUMENT_PROVIDER=simulated

WORKDIR /app

# Install Python deps first (better layer caching). Uses pyproject as the manifest.
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .

# Bring in the compiled SPA from the web stage.
COPY --from=web /build/app/static ./app/static

# Drop privileges.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
