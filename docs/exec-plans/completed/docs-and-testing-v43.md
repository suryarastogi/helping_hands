# Execution Plan: Docs and Testing v43

**Status:** Completed
**Created:** 2026-03-06
**Completed:** 2026-03-06
**Goal:** Cover remaining celery_app.py gaps (`_get_db_url_writer`, `ensure_usage_schedule`, `log_claude_usage` key paths); update ARCHITECTURE.md with usage monitoring section; update QUALITY_SCORE.md.

---

## Tasks

### Phase 1: celery_app.py coverage gaps

- [x] `_get_db_url_writer` env var override and default
- [x] `ensure_usage_schedule` (already-exists path, fresh-create path, import error path)
- [x] `log_claude_usage` (keychain failure, no token, API HTTP error, API generic error, DB write failure, success path, raw JWT token, non-JWT garbage)

### Phase 2: Documentation

- [x] Update ARCHITECTURE.md with usage monitoring section
- [x] Update QUALITY_SCORE.md with new test entries
- [x] Update docs/PLANS.md

### Phase 3: Validation

- [x] All tests pass (1653 passed)
- [x] Lint and format clean
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-3 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
