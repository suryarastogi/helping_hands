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
ARG CODEX_CLI_VERSION=0.80.0
ARG NODEJS_MAJOR=22
ARG GOOSE_CLI_VERSION=stable
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates bzip2 xz-utils libxcb1 \
    && retry() { \
        n=1; \
        until "$@"; do \
            if [ "$n" -ge 5 ]; then \
                return 1; \
            fi; \
            sleep $((n * 2)); \
            n=$((n + 1)); \
        done; \
    } \
    && install_node() { \
        case "$(uname -m)" in \
            x86_64) node_arch="x64" ;; \
            aarch64|arm64) node_arch="arm64" ;; \
            *) echo "Unsupported architecture: $(uname -m)" >&2; return 1 ;; \
        esac; \
        node_dist_url="https://nodejs.org/dist/latest-v${NODEJS_MAJOR}.x"; \
        node_tarball="$(curl -fsSL "${node_dist_url}/SHASUMS256.txt" | awk "/linux-${node_arch}\\.tar\\.xz$/ {print \$2; exit}")"; \
        if [ -z "${node_tarball}" ]; then \
            echo "Unable to resolve Node.js tarball for arch ${node_arch}" >&2; \
            return 1; \
        fi; \
        curl -fsSL "${node_dist_url}/${node_tarball}" | tar -xJ -C /usr/local --strip-components=1; \
    } \
    && install_goose() { \
        if [ "${GOOSE_CLI_VERSION}" = "stable" ]; then \
            curl -fsSL "https://github.com/block/goose/releases/download/${GOOSE_CLI_VERSION}/download_cli.sh" \
            | CONFIGURE=false bash; \
        else \
            curl -fsSL "https://github.com/block/goose/releases/download/${GOOSE_CLI_VERSION}/download_cli.sh" \
            | CONFIGURE=false GOOSE_VERSION="${GOOSE_CLI_VERSION}" bash; \
        fi; \
    } \
    && retry install_node \
    && retry install_goose \
    && npm config set fetch-retries 5 \
    && npm config set fetch-retry-factor 2 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && retry npm install -g "@openai/codex@${CODEX_CLI_VERSION}" \
    && install -m 0755 /root/.local/bin/goose /usr/local/bin/goose \
    && npm cache clean --force \
    && rm -rf /var/lib/apt/lists/*
RUN uv sync --frozen --no-dev --extra server --extra github --extra langchain --extra atomic

# Codex CLI: use OPENAI_API_KEY from env (default provider requires auth.json).
# See https://github.com/openai/codex/issues/5212
RUN mkdir -p /root/.codex \
    && printf '%s\n' \
    'model_provider = "openai-env-var"' \
    '[model_providers.openai-env-var]' \
    'name = "OpenAI (OPENAI_API_KEY)"' \
    'base_url = "https://api.openai.com/v1"' \
    'env_key = "OPENAI_API_KEY"' \
    'wire_api = "responses"' \
    > /root/.codex/config.toml

# Create non-root runtime user and mirror codex config.
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /home/app/.codex \
    && cp /root/.codex/config.toml /home/app/.codex/config.toml \
    && chown -R app:app /home/app /app

FROM app-deps AS server
ENV HOME=/home/app
USER app
CMD ["uv", "run", "uvicorn", "helping_hands.server.app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM app-deps AS worker
ENV HOME=/home/app
USER app
CMD ["uv", "run", "celery", "-A", "helping_hands.server.celery_app:celery_app", "worker", "--loglevel=info"]

FROM app-deps AS beat
ENV HOME=/home/app
USER app
CMD ["uv", "run", "celery", "-A", "helping_hands.server.celery_app:celery_app", "beat", "--loglevel=info"]

FROM app-deps AS flower
ENV HOME=/home/app
USER app
EXPOSE 5555
CMD ["uv", "run", "celery", "-A", "helping_hands.server.celery_app:celery_app", "flower", "--port=5555"]

FROM app-deps AS mcp
ENV HOME=/home/app
USER app
RUN uv sync --frozen --no-dev --extra server --extra github --extra langchain --extra atomic --extra mcp
EXPOSE 8080
CMD ["uv", "run", "helping-hands-mcp", "--http"]
