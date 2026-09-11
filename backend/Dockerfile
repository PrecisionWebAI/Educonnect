# syntax=docker/dockerfile:1
# ===========================================================================
# Educonnect backend — FastAPI + uv
#
# Multi-stage build:
#   builder  -> `uv sync --frozen` installs the exact dependency set from
#               uv.lock into /opt/venv (dev dependencies excluded)
#   runtime  -> slim Python image containing only the venv plus the files the
#               API needs at runtime (app/, alembic/, scripts/, alembic.ini)
#
# The app bootstraps itself on startup (creates DB/schema, runs Alembic
# migrations, seeds demo data) — see app/core/bootstrap.py.
# ===========================================================================

FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

WORKDIR /app

# ---------------------------------------------------------------------------
# Builder stage: install dependencies and the project itself
# ---------------------------------------------------------------------------
FROM base AS builder

# Official uv binary image (no curl/pip needed in the build)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_PROGRESS=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# Install the exact dependency set from the committed lockfile.
# --no-install-project keeps this layer cached unless pyproject/uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the backend and install the project into the venv.
COPY . .
RUN uv sync --frozen --no-dev

# ---------------------------------------------------------------------------
# Runtime stage: only the virtualenv + runtime files the API needs
# ---------------------------------------------------------------------------
FROM base AS runtime

COPY --from=builder /opt/venv /opt/venv

# Python package source, Alembic migrations + config, and the seed script
# (bootstrap loads scripts/seed.py on startup).
COPY --from=builder /app/app ./app
COPY --from=builder /app/alembic ./alembic
COPY --from=builder /app/alembic.ini ./alembic.ini
COPY --from=builder /app/scripts ./scripts

ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8000

# Same app as `make start`, pinned to uvicorn so the container command is
# explicit and dependency-light.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]