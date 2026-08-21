FROM node:20-slim AS web-build

WORKDIR /build/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/index.html web/vite.config.ts web/vitest.config.ts ./
COPY web/tsconfig*.json ./
COPY web/src ./src
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN groupadd -r app && useradd -r -g app app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY main.py ./
COPY --from=web-build /build/web/dist ./web/dist

RUN chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]