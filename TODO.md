# Project todos

## 1. Set up Python project under `src/hhpy/helping_hands`

- [x] **Layout** — Create `src/hhpy/helping_hands/` with package structure:
  - [x] `src/hhpy/helping_hands/lib/` — core library (repo, agent, config; used by both CLI and server)
  - [x] `src/hhpy/helping_hands/cli/` — CLI entry point and terminal UI (depends on lib only)
  - [x] `src/hhpy/helping_hands/server/` — app-mode server (depends on lib only, placeholder)
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

- [ ] **Docker** — Dockerise the app (e.g. `Dockerfile` for the helping_hands image used by server and workers).
- [ ] **Compose** — Add `docker-compose.yml` (or `compose.yaml`) with services:
  - [ ] **Main server** — Fast server (app mode) container.
  - [ ] **Workers** — Celery worker container(s).
  - [ ] **Redis** — Broker (and optional result backend) for Celery.
  - [ ] **Postgres** — Database for job metadata and app state.
  - [ ] **Flower** — Celery monitoring UI (optional but useful for debugging queues/tasks).
- [ ] Wire env/config so server and workers use the same Redis and Postgres (via Compose network and env vars).

## 3. Autodocs generation and serving on GitHub

- [ ] **Doc tool** — Add API docs generation (e.g. Sphinx with autodoc, or MkDocs with mkdocstrings) from docstrings in `lib`, `cli`, `server`.
- [ ] **Build in CI** — Run docs build in GitHub Actions (e.g. on push to main or a `docs` path).
- [ ] **Serve on GitHub** — Publish built docs to GitHub Pages (Actions workflow that deploys to `gh-pages` or via GitHub Pages source).

---

*Update this file as items are completed. Design notes live in `obsidian/docs/`.*
