# v206 — DRY payload validators, normalize selection, URL error handling

**Status:** Completed
**Created:** 2026-03-15

## Tasks

- [x] DRY payload validators in iterative.py — Remove 3 duplicated
  `_parse_str_list`/`_parse_positive_int`/`_parse_optional_str` static methods
  from `_BasicIterativeHand` and delegate to canonical implementations in
  `registry.py` via class attribute assignment
- [x] DRY `normalize_tool_selection`/`normalize_skill_selection` — Extract
  shared `_normalize_and_deduplicate(values, label)` helper to eliminate
  duplicated normalize/deduplicate logic between `registry.py` and
  `skills/__init__.py`
- [x] DRY URL error handling in `web.py` — Extract `_raise_url_error(exc,
  operation)` helper to consolidate duplicated HTTPError/URLError → RuntimeError
  pattern in both `search_web()` and `browse_url()`
- [x] Update source guard tests in `test_v151_input_type_validation.py` to
  reference `_normalize_and_deduplicate` instead of removed inline logic
- [x] Fix v205 plan missing `## Tasks` section
- [x] Add 30 new tests covering all changes

## Completion criteria

- All tasks implemented with tests
- `ruff check`, `ruff format`, `ty check`, `pytest` all pass
