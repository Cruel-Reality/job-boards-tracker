# syntax=docker/dockerfile:1
# slim (not alpine) so psycopg's glibc binary wheels work; uv comes preinstalled.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies before copying source so the (slow) dependency layer stays
# cached across code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# 0.0.0.0 so the server is reachable from outside the container, not just its loopback.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
