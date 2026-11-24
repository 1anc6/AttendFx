# One deployable image: the React web app (built here) and the FastAPI app (/mcp, /api, /healthz).
# Build from the repo root:  docker build -f infra/Dockerfile -t attendfx .

# --- Stage 1: build the web app -------------------------------------------------------------
FROM node:24-slim AS web
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: the runtime -------------------------------------------------------------------
FROM python:3.12-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/backend/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

# config.py finds the web build at <repo root>/frontend/dist, so the layout mirrors the repo.
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ ./
COPY --from=web /src/frontend/dist /app/frontend/dist

# Code stays root-owned and read-only for the runtime user. Nothing writes into /app at runtime.
RUN useradd --uid 10001 --no-create-home --user-group --shell /usr/sbin/nologin app
USER app

EXPOSE 8000

# Platforms set PORT (Render, Koyeb) or rely on the default. Migrations run first; they are
# idempotent, and they need AFX_OWNER_DATABASE_URL plus the three AFX_*_PASSWORD values.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
