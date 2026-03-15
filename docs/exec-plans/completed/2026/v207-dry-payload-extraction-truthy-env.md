# v207 — DRY payload extraction helper, truthy env var consistency

**Status:** Completed
**Created:** 2026-03-15

## Tasks

- [x] DRY `_extract_str_field(entry, keys)` helper in `server/app.py` —
  Consolidate the identical pattern from `_extract_task_id()` and
  `_extract_task_name()` into a shared recursive extractor with
  `_TASK_ID_KEYS` and `_TASK_NAME_KEYS` constant tuples
- [x] DRY truthy env var checks — Replace 3× inline
  `os.environ.get(...).strip().lower() in {truthy_set}` with
  `_is_truthy_env()` from `config.py`:
  - `pr_description.py` (`_is_disabled()`) — also drops inconsistent
    `"on"` to align with project-wide `_TRUTHY_VALUES`
  - `e2e.py` (`_draft_pr_enabled()`) — replaces inline
    `_TRUTHY_VALUES` import with `_is_truthy_env` delegation
  - `server/app.py` (`_is_running_in_docker()`) — removes unused
    `_TRUTHY_VALUES` import
- [x] Add `.strip()` to `_is_truthy_env()` in config.py for whitespace
  robustness consistency
- [x] Update existing tests (v165 e2e truthy import, pr_description
  parametrize) to match new implementation
- [x] Add 37 new tests (16 passed, 21 skipped without fastapi)
- [x] Run quality gates — all pass

## Completion criteria

- All tasks implemented with tests
- `ruff check`, `ruff format`, `ty check`, `pytest` all pass
