# Deployment Modes

How helping_hands runs in CLI, Server (FastAPI + Celery), and MCP modes.

## Context

helping_hands supports three distinct runtime modes that share the same core
library (`lib/`) but differ in how work is initiated, executed, and results are
delivered. Each mode targets a different usage pattern.

## CLI mode

**Entry point:** `uv run helping-hands <repo> --backend <backend> --prompt "..."`
**Module:** `cli/main.py`

The CLI parses arguments, builds a `Config`, indexes the repository, selects a
`Hand` subclass, and calls `run()` or `stream()` directly in-process. Results
are printed to stdout as they arrive.

Key characteristics:
- **Synchronous execution** -- the process blocks until the hand completes.
- **Local repository** -- operates on a local path or auto-clones `owner/repo`
  to a temp directory.
- **Direct streaming** -- `stream()` yields chunks printed to the terminal.
- **No external services** -- no Redis, Celery, or database required.
- **All backends available** -- iterative, CLI subprocess, and E2E hands.

Lifecycle:
```
CLI args -> Config -> RepoIndex -> Hand.stream()/run() -> stdout
```

## Server mode (FastAPI + Celery)

**Entry point:** `docker compose up` or `./scripts/run-local-stack.sh`
**Modules:** `server/app.py`, `server/celery_app.py`

The FastAPI app exposes HTTP endpoints (`/build`, `/tasks/{id}`) that enqueue
hand tasks via Celery. Workers execute hands asynchronously, storing results in
Redis. A React frontend or the inline HTML UI polls for status.

Key characteristics:
- **Asynchronous execution** -- tasks run in Celery workers, not the web process.
- **Persistent state** -- task status and results stored in Redis (result backend).
- **Multi-tenant** -- multiple tasks can run concurrently across workers.
- **Scheduling** -- optional RedBeat-based cron scheduling for recurring tasks.
- **Health checks** -- `/health` endpoint checks Redis, DB, and worker status.
- **Usage monitoring** -- optional Claude API usage tracking via keychain + DB.

Lifecycle:
```
HTTP POST /build -> Celery task -> Worker picks up -> Hand.stream() -> Redis
Frontend polls /tasks/{id} -> status + updates
```

Required infrastructure:
- Redis (broker + result backend)
- Optional: PostgreSQL (usage tracking, schedule persistence)
- Optional: Flower (worker monitoring)

## MCP mode

**Entry point:** `uv run helping-hands-mcp` (stdio) or `--http` (streamable HTTP)
**Module:** `server/mcp_server.py`

The MCP server exposes helping_hands capabilities as Model Context Protocol
tools, allowing AI clients (Claude Desktop, Cursor, etc.) to use the system
as a tool provider.

Key characteristics:
- **Tool-oriented** -- each capability is a discrete MCP tool, not a task queue.
- **Two transports** -- stdio for local clients, streamable HTTP for networked.
- **Repo isolation** -- tools operate within a validated repo root directory.
- **Shared filesystem layer** -- uses the same `meta/tools/filesystem.py` as
  hands for path-safe operations.
- **No Celery dependency** -- `build_feature` enqueues to Celery if available,
  but filesystem/execution tools run in-process.

Available tools:
- `index_repo` -- walk a repo and return its file listing
- `build_feature` -- enqueue an async hand task (Celery)
- `get_task_status` -- check task status
- `read_file`, `write_file`, `mkdir`, `path_exists` -- filesystem operations
- `run_python_code`, `run_python_script`, `run_bash_script` -- execution tools
- `web_search`, `web_browse` -- web tools

## Shared layer

All three modes share:
- **`lib/config.py`** -- configuration (env vars, CLI args, dotenv)
- **`lib/repo.py`** -- repository indexing
- **`lib/hands/v1/`** -- hand implementations
- **`lib/ai_providers/`** -- AI provider abstraction
- **`lib/meta/tools/`** -- filesystem, command, registry, web tools
- **`lib/github.py`** -- GitHub client for PR creation

The separation is enforced by import boundaries: `cli/` and `server/` depend on
`lib/`, but never import each other's internals.

## Decision: why three modes

| Concern | CLI | Server | MCP |
|---|---|---|---|
| User interaction | Terminal | Web UI | AI client |
| Concurrency | Single task | Multi-worker | Per-tool call |
| Infrastructure | None | Redis + workers | None (stdio) |
| Best for | Dev/scripting | Production/teams | AI integrations |

The three modes cover the full spectrum from local development (CLI), to team
deployment (Server), to AI-native integrations (MCP). Each adds infra
requirements proportional to the use case complexity.

## Consequences

- **Code duplication is minimal** -- mode-specific code is thin routing/glue.
- **Testing follows mode boundaries** -- CLI tests mock subprocess, server tests
  mock Celery/Redis, MCP tests mock filesystem calls.
- **New hands automatically work in all modes** -- they only need to implement
  `Hand.run()` and `Hand.stream()`.
- **Config is mode-agnostic** -- the same `Config` dataclass works everywhere,
  populated from args (CLI), form data (Server), or tool params (MCP).
