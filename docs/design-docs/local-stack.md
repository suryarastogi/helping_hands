# Local Stack

How helping_hands runs as a local development stack with data services in Docker
and application processes managed natively.

## Context

Full `docker compose up` rebuilds the entire application image on every code
change. For rapid local iteration the project provides
`scripts/run-local-stack.sh`, which keeps data services (Redis, PostgreSQL) in
Docker while running the application processes (FastAPI server, Celery worker,
beat scheduler, Flower monitor) as native `uv run` subprocesses. This gives
fast code-reload cycles without sacrificing service isolation for stateful
dependencies.

## Overview

```
┌──────────────────────────────────────────────────┐
│              Docker (data services)               │
│                                                   │
│   ┌──────────┐   ┌─────────────┐                 │
│   │  Redis    │   │  PostgreSQL │                 │
│   │  6379     │   │  5432       │                 │
│   └──────────┘   └─────────────┘                 │
└──────────────────────────────────────────────────┘
        │                   │
        ▼                   ▼
┌──────────────────────────────────────────────────┐
│          Native processes (uv run)                │
│                                                   │
│  ┌────────┐  ┌────────┐  ┌──────┐  ┌──────────┐ │
│  │ server │  │ worker │  │ beat │  │  flower  │ │
│  │ :8000  │  │        │  │      │  │  :5555   │ │
│  └────────┘  └────────┘  └──────┘  └──────────┘ │
└──────────────────────────────────────────────────┘
```

## Services

| Service | Command | Default port | Purpose |
|---|---|---|---|
| server | `uvicorn helping_hands.server.app:app` | 8000 | FastAPI HTTP API |
| worker | `celery -A ... worker --pool=threads --concurrency=4` | - | Task execution |
| beat | `celery -A ... beat` | - | Periodic task scheduler |
| flower | `celery -A ... flower` | 5555 | Worker monitoring UI |

## Lifecycle

### Start

1. Validate `uv` is on `PATH`.
2. Create runtime directories (`runs/local-stack/pids/`, `runs/local-stack/logs/`).
3. Load `.env` file (custom parser supporting `export`, quoted values, comments).
4. Set defaults for `SERVER_PORT`, `FLOWER_PORT`, `REDIS_URL`,
   `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.
5. Normalize Docker-oriented Redis URLs (`redis://redis:6379` becomes
   `redis://localhost:6379`) unless `HH_LOCAL_STACK_KEEP_DOCKER_HOSTS=1`.
6. Launch each service via `nohup` with stdout/stderr to
   `runs/local-stack/logs/<service>.log`.
7. Record PID to `runs/local-stack/pids/<service>.pid`.
8. Verify PID is alive after 300ms.

### Stop

1. Read PID file for each service.
2. Send `SIGTERM` and wait up to 5 seconds (20 polls at 250ms).
3. If still running, send `SIGKILL`.
4. Remove PID file.

Services are stopped in reverse dependency order: flower, beat, worker, server.

### Status

Reads PID files and checks whether each process is alive via `kill -0`.

### Logs

Tails log files with `tail -n 100 -f`. Accepts an optional service name filter.

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `SERVER_PORT` | `8000` | FastAPI listen port |
| `FLOWER_PORT` | `5555` | Flower UI port |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `CELERY_BROKER_URL` | `${REDIS_URL}` | Celery broker (defaults to REDIS_URL) |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Celery result store |
| `HH_LOCAL_STACK_KEEP_DOCKER_HOSTS` | `0` | Skip Redis URL normalization |
| `PYTHONUNBUFFERED` | `1` | Force unbuffered stdout (set by script) |

## Redis URL normalization

When `.env` is written for Docker Compose (e.g. `redis://redis:6379`), the
script auto-rewrites `redis://redis` to `redis://localhost` so that native
processes can reach the Docker-exposed Redis on localhost. This is skipped
when `HH_LOCAL_STACK_KEEP_DOCKER_HOSTS=1`.

## Runtime artifacts

All PID files and logs live under `runs/local-stack/`, which is gitignored.
The script creates this directory on first run.

## Decision: native processes vs full Docker

| Concern | Docker Compose | Local stack |
|---|---|---|
| Code reload | Rebuild image | Instant (uv run) |
| Data services | In-network | Docker-exposed on localhost |
| Isolation | Full container | Process-level only |
| Setup | `docker compose up` | `./scripts/run-local-stack.sh start` |
| Best for | CI / production-like | Rapid local development |

## Consequences

- Developers get fast iteration without rebuilding Docker images.
- Redis URL normalization avoids manual `.env` edits when switching between
  Docker Compose and local stack modes.
- PID-based management is simple but not bulletproof (orphan processes on
  unclean shutdown require manual cleanup).
- The `runs/` directory must be gitignored to avoid committing PID/log files.
