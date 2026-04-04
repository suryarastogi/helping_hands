# v347 — Test Coverage Gaps & Docs Structure Fix

**Status:** Active
**Created:** 2026-04-04

## Goal

Fix broken docs structure tests after README slimming (c7601f0), close
coverage gaps in `task_result.py`, `grill.py` Redis helpers. Update
documentation index to reflect moved content.

## Tasks

- [x] Fix 4 failing `test_docs_structure.py` tests (README sections changed,
      docs index missing references to `backends.md`, `app-mode.md`,
      `development.md`)
- [x] Add `task_result.py` unit tests (`normalize_task_result` — pure function,
      15 tests covering all branches: None, dict, exception, JSON-serializable,
      non-serializable, status validation)
- [x] Add `grill.py` Redis helper tests (`_set_state`, `_get_state`,
      `_push_ai_msg`, `_pop_user_msg` — 13 tests with mocked Redis)
- [x] Update `docs/index.md` to reference `backends.md`, `app-mode.md`,
      `development.md`
- [x] Update INTENT.md with active intent
- [ ] Move plan to completed when all work is done

## Notes

- `_redact_token` and `_is_recently_terminal` already had comprehensive test
  coverage (found in `test_server_app_coverage.py` and
  `test_server_app_helpers.py`)
- Grill helper tests require `--extra server` (celery dependency) — will pass
  in CI but skip locally without extras
- 28 new tests total (15 task_result + 13 grill helpers)

## Completion criteria

- All tests pass (`uv run pytest -v`)
- Coverage target ≥ 80% for newly-tested modules
- No ruff lint or format violations
