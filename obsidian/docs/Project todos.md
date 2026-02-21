# Project todos

The canonical checklist lives in the repo root: **`TODO.md`**. This note is for design notes or decisions that affect the todos.

## Summary (from TODO.md)

1. **Set up Python project** under `src/helping_hands`:
   - **Layout:** `lib/` (core), `cli/` (CLI, uses lib), `server/` (app mode, uses lib)
   - **Tooling:** uv, ruff, type checker (pyright/mypy), pre-commit
   - **CI/CD:** Strong pipeline (uv, tests, ruff, type check) on push/PR
   - **Tests:** pytest under `tests/`, run in CI

2. **Dockerise app mode and add Compose:** Dockerfile for the app; `docker-compose.yml` with main server, Celery workers, Redis, Postgres, and Flower.

3. **Autodocs generation and serving on GitHub:** Generate API docs from docstrings (e.g. Sphinx/MkDocs), build in CI, publish to GitHub Pages.

## Design notes

*(Add decisions or constraints here as they come up, e.g. "lib must have no server/cli imports.")*
