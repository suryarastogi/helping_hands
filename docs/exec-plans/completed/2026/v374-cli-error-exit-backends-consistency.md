# v374 — CLI Error Exit Backends Consistency

**Status:** Completed
**Created:** 2026-04-05

## Problem

`_CLI_ERROR_EXIT_BACKENDS` in `cli/main.py` is missing `opencodecli` and
`devincli`. When these CLI backends fail with `RuntimeError`, `ValueError`,
or `OSError`, the exception re-raises with a full stack trace instead of
printing a clean error message via `_error_exit()`.

All other CLI-backed hands (codexcli, claudecodecli, docker-sandbox-claude,
goose, geminicli) are already in the set and get clean error output.

## Tasks

- [x] Add `BACKEND_OPENCODECLI` and `BACKEND_DEVINCLI` to `_CLI_ERROR_EXIT_BACKENDS`
- [x] Add a structural consistency test verifying all CLI-tool-backed backends are in the set
- [x] Update the existing exact-match test
- [x] Add error-exit integration tests for the opencode and devin error paths

## Files

- `src/helping_hands/cli/main.py` — fix the frozenset
- `tests/test_v244_cli_error_constants_health_narrowing.py` — update exact-match test
- `tests/test_v374_cli_error_exit_consistency.py` — new consistency + error path tests

## Completion criteria

- `_CLI_ERROR_EXIT_BACKENDS` contains all 7 CLI backends
- Consistency test fails if a CLI backend is added without updating the set
- All tests pass, ruff clean
