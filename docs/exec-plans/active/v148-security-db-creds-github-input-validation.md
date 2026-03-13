## v148 — Remove hardcoded DB credentials, GitHubClient input validation

**Status:** Active
**Created:** 2026-03-13

## Goal

Two self-contained improvements:

1. **Remove hardcoded database credentials** — `_get_db_url_writer()` in `celery_app.py` (line 811) contains a hardcoded PostgreSQL connection string with plaintext credentials as a fallback default. Replace with a `RuntimeError` when `DATABASE_URL` is not set, consistent with secure-by-default practices.

2. **Add empty-string validation to GitHubClient branch/commit methods** — `create_branch`, `switch_branch`, `fetch_branch`, `add_and_commit` (message param), and `set_local_identity` (name/email params) accept empty strings without validation, which would produce confusing git subprocess errors. Add `ValueError` guards consistent with `_validate_full_name()` pattern already in the module.

## Tasks

- [x] Remove hardcoded DB credentials in `_get_db_url_writer()`, raise `RuntimeError` if `DATABASE_URL` not set
- [x] Add `_validate_branch_name()` helper to `github.py` (reject empty/whitespace)
- [x] Add validation to `create_branch`, `switch_branch`, `fetch_branch` for branch_name
- [x] Add validation to `add_and_commit` for empty message
- [x] Add validation to `set_local_identity` for empty name/email
- [x] Add tests for `_get_db_url_writer()` (5 tests: env set returns, no env raises, empty raises, whitespace raises, strips whitespace)
- [x] Add tests for `_validate_branch_name()` (5 tests: empty, whitespace, tab, valid branch, valid simple)
- [x] Add tests for GitHubClient method validation (11 tests: create_branch empty/ws, switch_branch empty/ws, fetch_branch empty/ws, add_and_commit empty/ws, set_local_identity empty/ws name, empty/ws email)
- [x] Run lint and tests — 3582 passing, 80 skipped
- [x] Update docs (PLANS.md, QUALITY_SCORE.md, Week-12)

## Completion criteria

- Hardcoded credentials removed from source code
- All GitHubClient branch/commit methods validate string inputs
- All new tests pass (19 new tests)
- `ruff check` and `ruff format` pass
