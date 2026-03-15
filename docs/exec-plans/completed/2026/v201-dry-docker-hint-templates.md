# v201 — DRY Docker hint message templates in CLI hands

**Status:** Completed
**Created:** 2026-03-15

## Problem

1. The auth failure Docker hint `"If running app mode in Docker, set {VAR} in .env
   and recreate server/worker containers."` is duplicated across 4 CLI hands
   (claude.py, codex.py, gemini.py, opencode.py).

2. The command-not-found Docker hint `"If running app mode in Docker, rebuild worker
   images so the {binary} binary is installed."` is duplicated across 4 CLI hands
   (codex.py, gemini.py, goose.py, opencode.py).

## Tasks

- [x] Extract `_DOCKER_ENV_HINT_TEMPLATE` in `cli/base.py`, replace 4× in auth failure messages
- [x] Extract `_DOCKER_REBUILD_HINT_TEMPLATE` in `cli/base.py`, replace 4× in command-not-found messages
- [x] Add `__all__` entries for new constants
- [x] Add tests for constant values, format args, and import identity
- [x] Update docs (Week-12, PLANS.md)

## Completion criteria

- All 8 Docker hint sites use shared templates from `cli/base.py`
- Tests pass, ruff clean
