# Execution Plan: Docs and Testing v28

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Increase test coverage for celery_app.py helper functions (70% -> 73%+) with pure function and async helper tests.

---

## Tasks

### Phase 1: celery_app.py unit tests

- [x] `_resolve_celery_urls` — all defaults (no env vars)
- [x] `_resolve_repo_path` — local directory path
- [x] `_resolve_repo_path` — invalid repo format raises ValueError
- [x] `_resolve_repo_path` — clone failure raises ValueError with redacted message
- [x] `_resolve_repo_path` — PR number adds `--no-single-branch`
- [x] `_update_progress` — callable update_state invoked with correct meta
- [x] `_update_progress` — non-callable update_state is no-op
- [x] `_update_progress` — workspace included in meta when set
- [x] `_has_gemini_auth` — empty string returns False
- [x] `_has_gemini_auth` — whitespace-only returns False
- [x] `_normalize_backend` — strips whitespace and lowercases
- [x] `_normalize_backend` — opencodecli is supported
- [x] `_normalize_backend` — e2e is supported
- [x] `_collect_stream` — collects chunks and calls update_progress

### Phase 2: Validation

- [x] All tests pass (1412 passed, 1 pre-existing failure, 6 skipped)
- [x] Lint and format clean
- [x] Update `docs/QUALITY_SCORE.md` with new coverage notes
- [x] Update `docs/PLANS.md`
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-2 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
