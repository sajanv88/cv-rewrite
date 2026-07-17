# One image that builds the React SPA and serves it from the FastAPI app.
# Build context is the repo root:  docker build -t cvrewrite .

# --- stage 1: build the SPA (React Router in SPA mode) ---------------------- #
FROM node:24-alpine AS web
RUN corepack enable
WORKDIR /web

# Install deps first for better layer caching, then build.
COPY cvrewriteui/package.json cvrewriteui/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY cvrewriteui/ ./
RUN pnpm run build          # -> /web/build/client (static assets + index.html)

# --- stage 2: resolve Python deps with uv into a venv ---------------------- #
FROM python:3.14-slim AS deps
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app

COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY api/ ./
RUN uv sync --frozen --no-dev

# --- runtime: slim image with the venv, the API, and the built SPA --------- #
FROM python:3.14-slim
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STATIC_DIR=/app/static

WORKDIR /app
COPY --from=deps /app /app
COPY --from=web /web/build/client /app/static

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
