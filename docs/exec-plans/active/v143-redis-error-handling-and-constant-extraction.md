## v143 — Redis write/delete error handling and constant extraction in schedules.py and goose.py

**Status:** Active
**Created:** 2026-03-12

## Goal

Three self-contained improvements:

1. **Redis write/delete/list error handling** (`schedules.py`) — `_save_meta()`, `_delete_meta()`, and `_list_meta_keys()` don't catch Redis errors, while `_load_meta()` already does (added in v128). A Redis failure in `_save_meta` silently loses schedule metadata; in `_delete_meta` it silently leaves stale data; in `_list_meta_keys` it crashes `list_schedules()`. Add try-except with warning logging for consistency.

2. **Extract `_SCHEDULE_ID_HEX_LENGTH = 12`** (`schedules.py`) — `generate_schedule_id()` uses `uuid.uuid4().hex[:12]` with a hardcoded magic number. Extract to module-level constant for discoverability.

3. **Extract `_OLLAMA_DEFAULT_HOST`** (`goose.py`) — `_resolve_ollama_host()` returns hardcoded `"http://localhost:11434"` as fallback. Extract to module-level constant for discoverability and testability.

## Tasks

- [x] Add try-except to `_save_meta()` with warning log, re-raise as `RuntimeError`
- [x] Add try-except to `_delete_meta()` with warning log (swallow, consistent with `_load_meta`)
- [x] Add try-except to `_list_meta_keys()` with warning log, return empty list on error
- [x] Extract `_SCHEDULE_ID_HEX_LENGTH = 12` in `schedules.py`
- [x] Extract `_OLLAMA_DEFAULT_HOST = "http://localhost:11434"` in `goose.py`
- [x] Add tests for all improvements (12 tests: 3 save_meta, 2 delete_meta, 3 list_meta_keys, 4 schedule_id_hex, 5 ollama_host — some overlap with existing)
- [x] Run lint and tests — 3487 passing, 52 skipped
- [x] Update docs (PLANS.md, QUALITY_SCORE.md, Week-11)

## Completion criteria

- All new tests pass (12 new tests)
- `ruff check` and `ruff format` pass
- Docs updated with v143 notes
