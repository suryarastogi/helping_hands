# v270 — `has_cli_flag()` helper, `install_hint()`, `_check_optional_dep()`

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17
**Tests:** 20 new (6254 passed, 273 skipped)

## Objective

Extract three small DRY helpers to eliminate duplicated patterns found across
CLI hands, server modules, and scheduling code.

## Tasks

- [x] Add `has_cli_flag()` to `validation.py` — replaces 5 inline `token == "--flag" or token.startswith("--flag=")` patterns
- [x] Add `install_hint()` to `validation.py` — replaces 5 inline `f"Install with: uv sync --extra {extra}"` patterns
- [x] Add `_check_optional_dep()` to `server/schedules.py` — replaces 2 near-identical `_check_redbeat()` / `_check_croniter()` functions
- [x] Update all call-sites: `cli/base.py`, `cli/codex.py`, `cli/gemini.py`, `cli/goose.py`, `cli/claude.py`, `cli/main.py`, `server/celery_app.py`, `server/app.py`, `server/schedules.py`
- [x] Add tests for all new helpers (~20 tests)
- [x] Update `__all__` in `validation.py` and fix existing `__all__` assertion tests
- [ ] Run full test suite — all pass
- [ ] Update docs (PLANS.md, daily consolidation)

## Completion criteria

- All 5 `token == "--flag" or token.startswith("--flag=")` patterns replaced with `has_cli_flag()`
- All 5 `"Install with: uv sync --extra ..."` patterns replaced with `install_hint()`
- `_check_redbeat()` and `_check_croniter()` delegate to `_check_optional_dep()`
- All new and existing tests pass
- Docs updated
