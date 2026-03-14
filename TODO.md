# Project todos

## 1. Set up Python project under `src/helping_hands`

- [x] **Layout** — Create `src/helping_hands/` with package structure:
  - [x] `src/helping_hands/lib/` — core library (repo, agent, config; used by both CLI and server)
  - [x] `src/helping_hands/cli/` — CLI entry point and terminal UI (depends on lib only)
  - [x] `src/helping_hands/server/` — app-mode server (depends on lib only, placeholder)
  - [x] `pyproject.toml` at repo root with project name `helping-hands`, uv-compatible
- [x] **Tooling**
  - [x] **uv** — venv and dependency management (`uv sync --dev`)
  - [x] **ruff** — Lint and format, config in `pyproject.toml`
  - [x] **ty** — Type checker config in `pyproject.toml`
  - [x] **pre-commit** — `.pre-commit-config.yaml` with ruff hooks
- [x] **CI/CD**
  - [x] GitHub Actions workflow (`.github/workflows/ci.yml`) on push/PR:
    - [x] Install with uv, run tests (Python 3.11, 3.12, 3.13)
    - [x] ruff check + ruff format
    - [ ] Type check step (add when ty has a stable CI runner)
    - [ ] Optional: build/publish or deploy steps
- [x] **Tests**
  - [x] `tests/` layout with test files for lib and cli (10 tests, all passing)
  - [x] pytest as runner, configured in `pyproject.toml`

## 2. Dockerise app mode and add Compose

- [x] **Docker** — Multi-stage `Dockerfile` (server, worker, beat, flower targets)
- [x] **Compose** — `compose.yaml` with services:
  - [x] **Main server** — FastAPI via uvicorn
  - [x] **Workers** — Celery worker container
  - [x] **Beat** — Celery Beat for scheduled tasks
  - [x] **Redis** — Broker with health check
  - [x] **Postgres** — Database with health check
  - [x] **Flower** — Celery monitoring UI
- [x] `.env.example` with all env vars; server and workers share Redis + Postgres via Compose network

## 3. Autodocs generation and serving on GitHub

- [x] **Doc tool** — MkDocs Material + mkdocstrings; `docs/` source with API reference pages for lib, cli, server
- [x] **Build in CI** — `.github/workflows/docs.yml` builds on push to main (docs/, mkdocs.yml, src/ changes)
- [x] **Serve on GitHub** — Deploys to GitHub Pages via `actions/deploy-pages`

## 4. Hand backend scaffolding vs implementation

- [x] **Dotenv bootstrap** — `Config.from_env()` loads `.env` from cwd and repo path (without overriding exported env vars)
- [x] **CLI hand scaffolds added** — `ClaudeCodeHand`, `CodexCLIHand`, and `GeminiCLIHand` placeholder backends exist in `src/helping_hands/lib/hands/v1/hand.py`
- [x] **Claude CLI execution** — Subprocess integration with command/env wiring, stdout/stderr handling, errors/timeouts (2026-03-14)
- [x] **Codex CLI execution** — Subprocess integration with command/env wiring, stdout/stderr handling, errors/timeouts (2026-03-14)
- [x] **Gemini CLI execution** — Subprocess integration with command/env wiring, stdout/stderr handling, errors/timeouts (2026-03-14)
- [x] **Backend selection/routing** — `--backend` CLI flag, `HELPING_HANDS_BACKEND` env var, `Config.backend` field, `create_hand()` factory (2026-03-14)
- [x] **Streaming for CLI hands** — All three CLI hands (Claude, Codex, Gemini) support async streaming via subprocess (2026-03-14)

---

*Update this file as items are completed. Design notes live in `obsidian/docs/`.*
