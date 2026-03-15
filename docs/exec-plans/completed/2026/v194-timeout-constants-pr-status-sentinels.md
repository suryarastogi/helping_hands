# v194 — DRY timeout constants and PR status sentinel extraction

**Status:** completed
**Created:** 2026-03-15
**Branch:** helping-hands/claudecodecli-bfc17b62

## Goal

Three self-contained DRY improvements:

1. **DRY script timeout** — Extract `_DEFAULT_SCRIPT_TIMEOUT_S = 60` in
   `command.py`, replacing 3× hardcoded `timeout_s: int = 60` defaults
   across `run_python_code`, `run_python_script`, `run_bash_script`.

2. **DRY web timeout** — Extract `_DEFAULT_WEB_TIMEOUT_S = 20` in `web.py`,
   replacing 2× hardcoded `timeout_s: int = 20` defaults across
   `search_web` and `browse_url`.

3. **PR status sentinels** — Extract 5 `_PR_STATUS_*` string constants and
   2 `_PR_STATUSES_*` frozensets in `base.py`, replacing ~17 scattered
   string literals across `base.py`, `iterative.py`, and `cli/base.py`.

## Tasks

- [x] Extract `_DEFAULT_SCRIPT_TIMEOUT_S` in `command.py`
- [x] Wire 3 function signatures to use the constant
- [x] Extract `_DEFAULT_WEB_TIMEOUT_S` in `web.py`
- [x] Wire 2 function signatures to use the constant
- [x] Extract `_PR_STATUS_CREATED/UPDATED/NO_CHANGES/DISABLED/NOT_ATTEMPTED` in `base.py`
- [x] Extract `_PR_STATUSES_WITH_URL` and `_PR_STATUSES_SKIPPED` frozensets
- [x] Replace string literals in `base.py` (6 occurrences)
- [x] Replace string literals in `iterative.py` (4 occurrences via `_PR_STATUSES_SKIPPED`)
- [x] Replace string literals in `cli/base.py` (6 occurrences via individual constants + frozenset)
- [x] Write 33 tests (6 command, 5 web, 12 sentinel, 4 frozenset, 6 cross-module)
- [x] Run all quality checks (ruff, ty, pytest)

## Completion criteria

- All script timeouts sourced from `_DEFAULT_SCRIPT_TIMEOUT_S` in `command.py`
- All web timeouts sourced from `_DEFAULT_WEB_TIMEOUT_S` in `web.py`
- All PR status strings sourced from `_PR_STATUS_*` constants in `base.py`
- All quality gates pass
- 4700 tests passed (+33 new), 155 skipped
