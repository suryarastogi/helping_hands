# Project todos

## 1. Set up Python project under `src/hhpy/helping_hands`

- [ ] **Layout** — Create `src/hhpy/helping_hands/` with package structure:
  - [ ] `src/hhpy/helping_hands/lib/` — core library (repo, agent, config; used by both CLI and server)
  - [ ] `src/hhpy/helping_hands/cli/` — CLI entry point and terminal UI (depends on lib only)
  - [ ] `src/hhpy/helping_hands/server/` — app-mode server (depends on lib only)
  - [ ] `pyproject.toml` at repo root (or under `src/hhpy/`) with project name `helping_hands`, uv-compatible
- [ ] **Tooling**
  - [ ] **uv** — Use uv for venv and dependency management (`uv init`, `uv add`, etc.)
  - [ ] **ruff** — Lint and format (`ruff check`, `ruff format`); add config in `pyproject.toml` or `ruff.toml`
  - [ ] **Type checker** — Configure strict type checking (e.g. pyright or mypy) in `pyproject.toml`
  - [ ] **pre-commit** — Add `.pre-commit-config.yaml` with hooks for ruff, type checker, and any other checks
- [ ] **CI/CD**
  - [ ] Workflow (e.g. GitHub Actions) that runs on push/PR:
    - [ ] Install with uv, run tests
    - [ ] ruff check + ruff format
    - [ ] Type check (pyright/mypy)
    - [ ] Optional: build/publish or deploy steps when you add them
- [ ] **Tests**
  - [ ] Test layout under `tests/` (or `src/hhpy/helping_hands/tests/`) that mirrors the package
  - [ ] pytest as runner; tests for lib (and later cli/server) that run in CI

## 2. Dockerise app mode and add Compose

- [ ] **Docker** — Dockerise the app (e.g. `Dockerfile` for the helping_hands image used by server and workers).
- [ ] **Compose** — Add `docker-compose.yml` (or `compose.yaml`) with services:
  - [ ] **Main server** — Fast server (app mode) container.
  - [ ] **Workers** — Celery worker container(s).
  - [ ] **Redis** — Broker (and optional result backend) for Celery.
  - [ ] **Postgres** — Database for job metadata and app state.
  - [ ] **Flower** — Celery monitoring UI (optional but useful for debugging queues/tasks).
- [ ] Wire env/config so server and workers use the same Redis and Postgres (via Compose network and env vars).

---

*Update this file as items are completed. Design notes live in `obsidian/docs/`.*
