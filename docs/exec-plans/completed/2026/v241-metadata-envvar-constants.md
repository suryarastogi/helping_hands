# v241 — Metadata key constants (backend/model/provider) and env var constants

**Status:** completed
**Created:** 2026-03-16
**Completed:** 2026-03-16

## Motivation

The metadata dictionary keys `"backend"`, `"model"`, and `"provider"` appear as bare
strings in 6 locations across `atomic.py`, `langgraph.py`, `iterative.py` (×2),
`cli/base.py`, and `e2e.py`. Similarly, the env var names `"GIT_TERMINAL_PROMPT"` and
`"GCM_INTERACTIVE"` appear 5 times each in `base.py` and twice in `github_url.py`.

Extracting these into module-level constants follows the established `_META_*` pattern
and eliminates typo risk.

## Changes

### Code changes

- **Added `_META_BACKEND`, `_META_MODEL`, `_META_PROVIDER`** to `base.py` —
  metadata key constants for execution backend, model identifier, and provider name
- **Added `_ENV_GIT_TERMINAL_PROMPT`, `_ENV_GCM_INTERACTIVE`** to `base.py` —
  env var name constants used in `_push_noninteractive()`
- **Added `_ENV_GIT_TERMINAL_PROMPT`, `_ENV_GCM_INTERACTIVE`** to `github_url.py` —
  env var name constants used in `noninteractive_env()`
- **Replaced 10 bare `"GIT_TERMINAL_PROMPT"`/`"GCM_INTERACTIVE"` strings** in
  `base.py` `_push_noninteractive()` with `_ENV_*` constants
- **Replaced 2 bare env var strings** in `github_url.py` `noninteractive_env()`
- **Replaced 3 bare `"backend"`/`"model"`/`"provider"` dict keys** in `atomic.py`
- **Replaced 3 bare dict keys** in `langgraph.py`
- **Replaced 6 bare dict keys** in `iterative.py` (2× run() methods)
- **Replaced 2 bare dict keys** in `cli/base.py`
- **Replaced 2 bare dict keys** in `e2e.py`

### Tasks completed

- [x] Add `_META_BACKEND`, `_META_MODEL`, `_META_PROVIDER` to base.py
- [x] Add `_ENV_GIT_TERMINAL_PROMPT`, `_ENV_GCM_INTERACTIVE` to base.py
- [x] Add `_ENV_GIT_TERMINAL_PROMPT`, `_ENV_GCM_INTERACTIVE` to github_url.py
- [x] Replace bare strings in base.py `_push_noninteractive()`
- [x] Replace bare strings in atomic.py
- [x] Replace bare strings in langgraph.py
- [x] Replace bare strings in iterative.py
- [x] Replace bare strings in cli/base.py
- [x] Replace bare strings in e2e.py
- [x] Replace bare strings in github_url.py
- [x] Add tests (35 tests)
- [x] Update PLANS.md

## Test results

- 35 new tests added (all passed)
- 5770 passed, 239 skipped (no regressions)
- All lint/format checks pass

## Completion criteria

- [x] All tasks checked
- [x] `uv run pytest` passes with no new failures
- [x] `uv run ruff check .` passes
- [x] `uv run ruff format --check .` passes
