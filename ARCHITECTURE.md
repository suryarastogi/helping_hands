# Architecture

High-level view of helping_hands. For working-on-the-code guidance, see
[AGENT.md](AGENT.md). For multi-agent coordination, see [AGENTS.md](AGENTS.md).

## System overview

```
                         helping_hands
                    ┌─────────────────────┐
                    │                     │
     CLI mode ──────┤  Config             │
                    │    ↓                │
     App mode ──────┤  Repo (ingest)      │
       (FastAPI +   │    ↓                │
        Celery)     │  Hand (AI backend)  │
                    │    ↓                │
     MCP server ────┤  Response / Stream  │
                    │                     │
                    └─────────────────────┘
```

## Layers

### 1. Entry points

- **CLI** (`cli/main.py`): Parses args, loads config, indexes repo, runs hand.
- **Server** (`server/app.py`): FastAPI HTTP API that enqueues Celery tasks.
- **MCP** (`server/mcp_server.py`): Model Context Protocol server for AI
  clients (Claude Desktop, Cursor).

### 2. Core library (`lib/`)

- **Config** (`config.py`): Immutable dataclass. Priority: CLI flags > env
  vars > `.env` files > defaults. No global state.
- **Repo** (`repo.py`): Walks a git repo, builds `RepoIndex` (root path +
  file listing). Excludes `.git/`.
- **GitHub** (`github.py`): Authenticated client wrapping PyGithub. Clone,
  branch, commit, push, create/list PRs.
- **Hands** (`hands/v1/hand.py`): Abstract `Hand` base class + backends.
  Each backend implements `run()` (sync) and `stream()` (async generator).

### 3. Hand backends

| Backend | How it works |
|---|---|
| `LangGraphHand` | Creates a LangChain ReAct agent via `create_react_agent` |
| `AtomicHand` | Uses atomic-agents with instructor for structured output |
| `ClaudeCodeHand` | Runs Claude Code CLI as subprocess, captures stdout |
| `CodexCLIHand` | Scaffold — will run Codex CLI as subprocess |
| `GeminiCLIHand` | Scaffold — will run Gemini CLI as subprocess |

Backend selection is via `Config.backend` field (CLI `--backend` flag or
`HELPING_HANDS_BACKEND` env var).

### 4. App mode stack

```
Client → FastAPI → Redis (broker) → Celery worker → Hand → result
                                  → Celery Beat (scheduled tasks)
                                  → Postgres (job metadata)
                                  → Flower (monitoring UI)
```

## Data flow

### CLI mode
```
User → CLI → Config.from_env()
         → RepoIndex.from_path()
         → Hand(config, repo_index).run(prompt)
         → streamed response to terminal
```

### App mode
```
Client → POST /build → Celery task queued
Worker → Config → RepoIndex → Hand → result stored in backend
Client → GET /tasks/{id} → poll for result
```

## Design principles

- **Plain data between layers**: Dicts and dataclasses, not tight coupling.
- **Streaming by default**: AI output streams as it arrives.
- **Explicit config**: No singletons. Config loaded once, passed through.
- **Backend-agnostic**: All hands implement the same `Hand` protocol.

## Key files

| File | Purpose |
|---|---|
| `src/helping_hands/lib/config.py` | Configuration loading |
| `src/helping_hands/lib/repo.py` | Repo ingestion |
| `src/helping_hands/lib/github.py` | GitHub API client |
| `src/helping_hands/lib/hands/v1/hand.py` | Hand backends |
| `src/helping_hands/cli/main.py` | CLI entry point |
| `src/helping_hands/server/app.py` | FastAPI server |
| `src/helping_hands/server/celery_app.py` | Celery tasks |
| `src/helping_hands/server/mcp_server.py` | MCP server |
| `pyproject.toml` | Project config |
| `AGENT.md` | AI agent working guidelines |
| `AGENTS.md` | Multi-agent coordination |
