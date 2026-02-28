# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Install (Python 3.12+, uses uv)
uv sync --dev
uv sync --extra langchain --extra atomic --extra server --extra github --extra mcp

# Run CLI
uv run helping-hands <local-path-or-owner/repo> --backend basic-langgraph --model gpt-5.2 --prompt "task"

# Run MCP server
uv run helping-hands-mcp              # stdio mode
uv run helping-hands-mcp --http       # HTTP mode

# Lint & format
uv run ruff check .                   # lint
uv run ruff check --fix .             # lint with autofix
uv run ruff format --check .          # format check
uv run ruff format .                  # format

# Type check
uv run ty check src --ignore unresolved-import --ignore invalid-method-override

# Tests
uv run pytest -v                      # all tests with coverage
uv run pytest tests/test_config.py -v # single test file
uv run pytest -k test_name -v         # single test by name

# Pre-commit hooks
uv run pre-commit install
uv run pre-commit run --all-files

# Frontend (from repo root)
npm --prefix frontend install
npm --prefix frontend run dev         # dev server
npm --prefix frontend run build
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test

# App mode (Docker)
docker compose up --build
# Or local stack (data services in Docker, app processes local):
./scripts/run-local-stack.sh start
```

## Architecture

**`helping_hands` is an AI-powered repo builder** — point it at a codebase and it uses AI to add features, fix bugs, and evolve code. Runs as CLI, FastAPI server (with Celery workers), or MCP server.

### Core abstraction: Hands

Everything flows through the **Hand** base class (`src/helping_hands/lib/hands/v1/hand/base.py`). Hands are the execution backends — each one implements `run()`/`stream()` and represents a different approach to AI-driven code changes:

- **E2EHand** (`e2e.py`) — clone/edit/commit/push/PR flow for integration testing
- **_BasicIterativeHand** (`iterative.py`) — base for loop-based hands with `@@READ`/`@@FILE` in-model file operations
- **BasicLangGraphHand** (`iterative.py`) — LangGraph-backed iterative hand (requires `--extra langchain`)
- **BasicAtomicHand** (`iterative.py`) — Atomic-backed iterative hand (requires `--extra atomic`)
- **LangGraphHand** (`langgraph.py`) — standalone LangGraph agent (requires `--extra langchain`)
- **AtomicHand** (`atomic.py`) — standalone Atomic Agents agent (requires `--extra atomic`)
- **CLI Hands** (`cli/`) — subprocess wrappers around external CLIs: `codex.py`, `claude.py`, `goose.py`, `gemini.py`

Finalization (commit/push/PR) is centralized in the base `Hand` class. All hands attempt it by default; disable with `--no-pr`.

### Provider abstraction

AI providers live in `src/helping_hands/lib/ai_providers/` with a common `AIProvider` interface. Models are specified as bare strings (`gpt-5.2`) or `provider/model` format (`anthropic/claude-sonnet-4-5`). Resolution happens in `model_provider.py`.

### Module boundaries

- `src/helping_hands/lib/` — core library (config, repo indexing, GitHub API, hands, meta tools, AI providers)
- `src/helping_hands/cli/` — CLI entry point, depends on lib
- `src/helping_hands/server/` — FastAPI app + Celery tasks + MCP server, depends on lib
- `frontend/` — React + TypeScript + Vite UI
- `tests/` — pytest suite

These layers communicate through plain data (dicts, dataclasses), not by importing each other's internals.

### System tool isolation

All filesystem/command operations for hands route through `src/helping_hands/lib/meta/tools/filesystem.py` for path-safe behavior (prevents path traversal via `resolve_repo_target()`). MCP tools use the same layer.

## Code Conventions

- **Python 3.12+**, `uv` for package management
- **Formatter/linter**: `ruff` (line length 88, rules: E, W, F, I, N, UP, B, SIM, RUF)
- **Type hints everywhere**: prefer `X | None` over `Optional[X]`
- **Imports**: absolute (`from helping_hands.lib.config import Config`), grouped as stdlib → third-party → local
- **Naming**: `snake_case` functions/variables, `PascalCase` classes, `_` prefix for private helpers
- **Docstrings**: Google-style, required for public functions/classes
- **Tests**: pytest in `tests/`, coverage enabled by default in pytest config
- **No global state**: configuration is passed explicitly, no module-level singletons
- **Streaming-first**: AI responses should be streamable as they arrive

## Key Architectural Decisions

- Hand implementations stay split under `hands/v1/hand/` — avoid regressing to a monolithic `hand.py`
- Iterative hands preload `README.md`, `AGENT.md`, and bounded repo tree snapshot on iteration 1
- Git push uses token-authenticated (`GITHUB_TOKEN`) non-interactive remotes
- `owner/repo` CLI inputs are auto-cloned to temp workspaces
- `AGENT.md` is a living document that AI agents update as they learn repo conventions

## CI

GitHub Actions runs on Python 3.12/3.13/3.14: ruff lint + format check, pytest with coverage, Codecov upload. Frontend CI runs lint, typecheck, and Vitest with coverage separately.
