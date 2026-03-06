# Execution Plan: Docs and Testing v35

**Status:** Completed
**Created:** 2026-03-06
**Completed:** 2026-03-06
**Goal:** Add server/app.py health check and config helper tests; add celery_app.py _has_codex_auth tests; update DESIGN.md with health check patterns.

---

## Tasks

### Phase 1: server/app.py health check and config helper tests

- [x] `_check_redis_health` (ok/error paths)
- [x] `_check_db_health` (ok/error/na paths)
- [x] `_check_workers_health` (ok/none/empty/exception paths)
- [x] `_is_running_in_docker` (dockerenv/env var true/1/no/neither)
- [x] `_iter_worker_task_entries` (valid/non-dict/non-list/non-dict entries)
- [x] `_safe_inspect_call` (success/missing method/exception)

### Phase 2: celery_app.py _has_codex_auth tests

- [x] `_has_codex_auth` (env var set, auth file exists, neither, empty key)

### Phase 3: Documentation and validation

- [x] Update DESIGN.md with health check and server config patterns
- [x] Update docs/QUALITY_SCORE.md
- [x] All tests pass (1514 passed)
- [x] Lint and format clean
- [x] Update docs/PLANS.md
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-3 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
