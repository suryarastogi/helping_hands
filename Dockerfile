FROM python:3.11-slim AS base

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
COPY README.md LICENSE ./
RUN uv sync --frozen --no-dev

FROM base AS server
CMD ["uv", "run", "uvicorn", "hhpy.helping_hands.server.app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS worker
CMD ["uv", "run", "celery", "-A", "hhpy.helping_hands.server.celery_app:celery_app", "worker", "--loglevel=info"]

FROM base AS beat
CMD ["uv", "run", "celery", "-A", "hhpy.helping_hands.server.celery_app:celery_app", "beat", "--loglevel=info"]

FROM base AS flower
EXPOSE 5555
CMD ["uv", "run", "celery", "-A", "hhpy.helping_hands.server.celery_app:celery_app", "flower", "--port=5555"]
