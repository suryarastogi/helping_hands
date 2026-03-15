# v200 — DRY timestamp helper, truthy env check, UUID hex length

**Status:** Completed
**Created:** 2026-03-15

## Problem

1. `datetime.now(UTC).replace(microsecond=0).isoformat()` is repeated 4× across
   `base.py` (3×) and `e2e.py` (1×) — should be a named helper.

2. `celery_app.py` line 123 uses an inline `("1", "true", "yes")` tuple instead
   of the shared `_TRUTHY_VALUES` frozenset from `config.py`.

3. `docker_sandbox_claude.py` defines `_SANDBOX_UUID_HEX_LENGTH = 8` which
   duplicates `_UUID_HEX_LENGTH = 8` from `base.py`.

## Tasks

- [x] Extract `_utc_stamp()` helper in `base.py`, replace 3× usages in base.py
- [x] Import and use `_utc_stamp` in `e2e.py`, replacing 1× usage
- [x] Import `_TRUTHY_VALUES` in `celery_app.py`, replace inline tuple
- [x] Import `_UUID_HEX_LENGTH` in `docker_sandbox_claude.py`, remove local duplicate
- [x] Add tests for `_utc_stamp()`, celery truthy import, UUID constant identity
- [x] Update docs (Week-12, PLANS.md)

## Completion criteria

- All 4 timestamp sites use `_utc_stamp()`
- Celery truthy check uses shared constant
- Docker sandbox UUID uses shared constant
- Tests pass, ruff clean
