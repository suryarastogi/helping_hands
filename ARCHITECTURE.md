# Architecture

> System-level overview of helping_hands. For code conventions, see [AGENT.md](AGENT.md). For build commands, see [CLAUDE.md](CLAUDE.md).

## Runtime Modes

helping_hands runs in three modes, all sharing the same core library:

```
CLI (cli/main.py)  ──┐
FastAPI (server/)  ───┤──▶  lib/  ──▶  AI Providers  ──▶  LLM
MCP (server/mcp)  ───┘         │
                               ├── hands/      (execution backends)
                               ├── meta/tools/ (filesystem, commands, web)
                               ├── config.py   (explicit config passing)
                               ├── repo.py     (repo indexing)
                               └── github.py   (PR/push helpers)
```

## Core Abstraction: Hands

The **Hand** base class (`lib/hands/v1/hand/base.py`) defines the execution contract. Every backend implements `run()`/`stream()` and returns a `HandResponse`.

| Hand | Module | Description |
|------|--------|-------------|
| E2EHand | `e2e.py` | Clone/edit/commit/push/PR integration flow |
| IterativeHand | `iterative.py` | Loop-based with `@@READ`/`@@FILE` in-model file ops |
| BasicLangGraphHand | `langgraph.py` | LangGraph agent loop |
| BasicAtomicHand | `atomic.py` | Atomic Agents loop |
| CLI Hands | `cli/` | Subprocess wrappers: codex, claude, goose, gemini, opencode |

Finalization (commit/push/PR) is centralized in the base Hand class.

## AI Providers

Providers in `lib/ai_providers/` implement a common `AIProvider` interface with `complete()` and `acomplete()`. Model strings resolve through `model_provider.py`:

- Bare strings (`gpt-5.2`) → default provider resolution
- Qualified strings (`anthropic/claude-sonnet-4-5`) → explicit provider

## Security Boundary

All filesystem operations route through `lib/meta/tools/filesystem.py` which enforces:

- Path confinement via `resolve_repo_target()` — prevents traversal outside repo root
- UTF-8 text validation on reads
- Normalized forward-slash paths

## Server Mode

```
FastAPI (app.py)
  ├── REST endpoints for task submission/status
  ├── WebSocket streaming for real-time output
  ├── Inline HTML UI (_UI_HTML)
  └── Celery task dispatch

Celery (celery_app.py)
  ├── Redis broker
  ├── Task workers executing Hand.run()
  └── RedBeat scheduler for recurring tasks

MCP Server (mcp_server.py)
  └── Model Context Protocol tool surface
```

## Frontend

React + TypeScript + Vite app in `frontend/`. Must stay in sync with the inline HTML UI in `app.py` (see AGENT.md recurring decisions).

## Module Boundaries

Layers communicate through plain data (dicts, dataclasses). No cross-layer internal imports:

- `lib/` — core library, no server/CLI deps
- `cli/` — depends on lib only
- `server/` — depends on lib only
- `frontend/` — talks to server via HTTP/WS
