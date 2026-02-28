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
- **_BasicIterativeHand / BasicLangGraphHand / BasicAtomicHand** (`iterative.py`) — shared loop base and concrete iterative backends with `@@READ`/`@@FILE` in-model file operations (`basic-agent` is a CLI alias for `BasicAtomicHand`)
- **LangGraphHand** (`langgraph.py`) — direct (non-iterative) LangGraph agent (requires `--extra langchain`)
- **AtomicHand** (`atomic.py`) — direct (non-iterative) Atomic Agents agent (requires `--extra atomic`)
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

All filesystem/command/web operations for hands route through `src/helping_hands/lib/meta/tools/` — `filesystem.py` (path-safe file ops), `command.py` (Python/bash execution), and `web.py` (search/browse). MCP tools use the same layer.

### Dynamic skills

Composable capability bundles live in `src/helping_hands/lib/meta/skills/`. Skills (`execution`, `web`, `prd`, `ralph`) inject tool definitions and prompt instructions into iterative hands. Selected via `--skills` CLI flag or `/build` API parameter.

## Code Conventions & Design

See [AGENT.md](AGENT.md) for the full living reference on code style, design
preferences, tone, recurring decisions, and dependencies. Key points:

- **Python 3.12+**, `uv`, `ruff` (line 88), `ty` type checker
- **Type hints everywhere**: `X | None` over `Optional[X]`
- **Imports**: absolute, grouped stdlib → third-party → local
- **Naming**: `snake_case` functions/variables, `PascalCase` classes
- **Docstrings**: Google-style for public APIs
- **No global state**; **streaming-first**
- Hand implementations stay split under `hands/v1/hand/` — no monolithic `hand.py`

## CI

GitHub Actions runs on Python 3.12/3.13/3.14: ruff lint + format check, pytest with coverage, Codecov upload. Frontend CI runs lint, typecheck, and Vitest with coverage separately.
