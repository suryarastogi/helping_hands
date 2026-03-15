# v207 — DRY shared validation helpers

**Status:** Completed
**Created:** 2026-03-15

## Summary

Extract duplicated validation patterns into a shared `validation.py` module:
- `require_non_empty_string(value, name)` — consolidates 24 occurrences of
  `if not X or not X.strip()` across 8 source files
- `require_positive_int(value, name)` — consolidates 15+ occurrences of
  `if value <= 0: raise ValueError(...)` across 7 source files

## Tasks

- [x] Create `src/helping_hands/lib/validation.py` with `require_non_empty_string`
  and `require_positive_int` helpers
- [x] Apply `require_non_empty_string` to: `github.py` (8 sites),
  `mcp_server.py` (6 sites), `base.py` (4 sites), `pr_description.py` (3 sites),
  `github_url.py` (1 site), `app.py` (1 site — `_validate_path_param` delegation)
- [x] Apply `require_positive_int` to: `github.py` (5 sites),
  `filesystem.py` (2 sites), `web.py` (4 sites), `pr_description.py` (2 sites),
  `command.py` (1 site)
- [x] Add 36 tests in `tests/test_v207_shared_validators.py`
- [x] All quality gates pass: ruff check, ruff format, ty check, pytest

## Completion criteria

- All tasks implemented with tests
- `ruff check`, `ruff format`, `ty check`, `pytest` all pass
- 4999 passed, 216 skipped
