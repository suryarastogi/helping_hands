# v199 — DRY registry.py default constants

**Status:** Active
**Created:** 2026-03-15

## Problem

`registry.py` hardcodes 7 default values that duplicate constants already defined in
`command.py` and `web.py`:

- `60` (script timeout) × 3 — duplicates `command._DEFAULT_SCRIPT_TIMEOUT_S`
- `"3.13"` (Python version) × 2 — duplicates `command.py` function defaults
- `20` (web timeout) × 2 — duplicates `web._DEFAULT_WEB_TIMEOUT_S`
- `5` (search max results) × 1 — no named constant exists yet

## Tasks

- [x] Extract `_DEFAULT_PYTHON_VERSION = "3.13"` in `command.py` and use in function defaults
- [x] Extract `DEFAULT_SEARCH_MAX_RESULTS = 5` in `web.py` and add to `__all__`
- [x] Import `_DEFAULT_SCRIPT_TIMEOUT_S` from `command.py` in `registry.py`
- [x] Import `_DEFAULT_WEB_TIMEOUT_S` and `DEFAULT_SEARCH_MAX_RESULTS` from `web.py` in `registry.py`
- [x] Replace all 7 hardcoded literals in `registry.py` runner wrappers
- [x] Add tests for new constants and imports
- [x] Update docs

## Completion criteria

- All 7 literals replaced with named imports
- Tests pass
- Ruff clean
