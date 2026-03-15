# v198 — Request validation hardening and DRY form defaults

**Created:** 2026-03-15
**Status:** Completed

## Goal

Harden server request validation for `pr_number`, `github_token`, and
`reference_repos` fields in `BuildRequest`/`ScheduleRequest`. Fix a hardcoded
default in `_build_form_redirect_query`. Add query length validation to
`search_web`.

## Tasks

- [x] **DRY `_build_form_redirect_query` CI wait default:** Replace hardcoded
  `3.0` with `_DEFAULT_CI_WAIT_MINUTES` constant (param default and comparison
  in `app.py`)
- [x] **`pr_number` positive validation:** Add `Field(default=None, ge=1)` to
  `BuildRequest.pr_number` and `ScheduleRequest.pr_number`
- [x] **`github_token` whitespace normalization:** Add `@field_validator` that
  converts whitespace-only strings to `None`
- [x] **`reference_repos` item validation:** Add `@field_validator` that rejects
  empty/whitespace-only strings in the list
- [x] **`search_web` query length validation:** Add `MAX_SEARCH_QUERY_LENGTH`
  constant and validate in `search_web()`
- [x] **Tests:** 31 new tests (26 skipped without fastapi, 5 web tests)

## Completion criteria

- All 5 changes implemented with tests
- `uv run ruff check .` clean
- `uv run ruff format --check .` clean
- `uv run pytest -v` passes — 4743 passed, 218 skipped
