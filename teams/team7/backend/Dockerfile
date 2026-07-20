# syntax=docker/dockerfile:1.7

# ---------- Stage 1: build dependencies with uv --------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS builder
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies first (better layer caching).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy the project source and install it (with dev deps so `pytest` works
# inside the image; the CMD below is uvicorn — dev deps only run in tests).
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
RUN uv sync --frozen


# ---------- Stage 2: minimal runtime image -------------------------------------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

# Create a non-root user for the runtime.
RUN groupadd --system app && useradd --system --gid app --home /app app

# Keep pytest's cache outside /app (read-only for the non-root user).
ENV PYTEST_CACHE_DIR=/tmp/.pytest_cache

# Copy the prepared virtual environment and project files from the builder.
COPY --from=builder /app /app

USER app

EXPOSE 8000

# Default command: uvicorn for FastAPI on port 8000.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
