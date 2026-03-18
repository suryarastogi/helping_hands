# v272 — MCP path error helper, CLI config overrides DRY, narrow CLI exception

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17
**Tests:** 20 new (6298 passed, 273 skipped)

## Objective

Three self-contained improvements continuing the DRY refactoring campaign:

1. **MCP server: `_reraise_path_error()` helper** — The `read_file`, `write_file`,
   and `mkdir` tools each wrap filesystem exceptions with contextual messages using
   near-identical try/except blocks. Extract a helper to DRY the pattern.

2. **CLI: `_build_config_overrides()` helper** — `main()` builds two nearly
   identical `dict[str, ConfigValue]` dicts (`e2e_overrides` and `run_overrides`)
   differing only in `repo` value. Extract a shared helper.

3. **CLI: narrow `except Exception`** — Catches broad `Exception` and
   string-matches for model-not-found markers. Narrow to
   `(RuntimeError, ValueError, OSError)` which covers the actual exceptions
   raised by `create_hand()` and `_stream_hand()`.

## Tasks

- [x] Add `_reraise_path_error()` to `mcp_server.py`
- [x] Refactor `read_file`, `write_file`, `mkdir` to use the helper
- [x] Add `_build_config_overrides()` to `cli/main.py`
- [x] Refactor `main()` to use the helper for both e2e and run overrides
- [x] Narrow `except Exception` to `(RuntimeError, ValueError, OSError)` in `main()`
- [x] Add 9 tests for `_reraise_path_error()`
- [x] Add 5 tests for `_build_config_overrides()`
- [x] Add 6 tests for the narrowed exception handling
- [x] Update existing `test_cli_model_not_found_exits_with_message` to use
      `RuntimeError` instead of bare `Exception`
- [x] Run full test suite — 6298 passed, 273 skipped
- [x] Update docs

## Completion criteria

- 6 MCP `msg = f"..."; raise ...` blocks → 6 `_reraise_path_error()` delegations
- 2 near-identical 10-key config override dicts → 1 `_build_config_overrides()` call each
- `except Exception` → `except (RuntimeError, ValueError, OSError)`
- All existing tests pass
- 20 new tests cover the extracted helpers and narrowed exception
