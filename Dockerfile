FROM python:3.12-slim AS base

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
COPY README.md LICENSE ./
RUN uv sync --frozen --no-dev

FROM base AS app-deps
RUN uv sync --frozen --no-dev --extra server --extra github --extra langchain --extra atomic

FROM app-deps AS server
CMD ["uv", "run", "uvicorn", "helping_hands.server.app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM app-deps AS worker
CMD ["uv", "run", "celery", "-A", "helping_hands.server.celery_app:celery_app", "worker", "--loglevel=info"]

FROM app-deps AS beat
CMD ["uv", "run", "celery", "-A", "helping_hands.server.celery_app:celery_app", "beat", "--loglevel=info"]

FROM app-deps AS flower
EXPOSE 5555
CMD ["uv", "run", "celery", "-A", "helping_hands.server.celery_app:celery_app", "flower", "--port=5555"]

FROM app-deps AS mcp
RUN uv sync --frozen --no-dev --extra server --extra github --extra langchain --extra atomic --extra mcp
EXPOSE 8080
CMD ["uv", "run", "helping-hands-mcp", "--http"]
