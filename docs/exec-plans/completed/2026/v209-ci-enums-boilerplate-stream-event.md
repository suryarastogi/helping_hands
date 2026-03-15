# v209 — CI status enums, boilerplate prefix optimization, stream event constant

**Status:** Completed
**Created:** 2026-03-15

## Summary

Three self-contained improvements across the CI fix loop, PR description parsing,
and LangGraph streaming:

1. **`CIConclusion` StrEnum** in `github.py` — Replace 5 hardcoded CI conclusion
   strings (`"no_checks"`, `"pending"`, `"success"`, `"failure"`, `"mixed"`) with
   a single enum. Adds `CI_CONCLUSIONS_IN_PROGRESS` frozenset and
   `_CI_RUN_FAILURE_CONCLUSIONS` frozenset for individual check-run failure
   conclusions (`"failure"`, `"cancelled"`, `"timed_out"`).

2. **`CIFixStatus` StrEnum** in `cli/base.py` — Replace 7 hardcoded CI fix loop
   status strings (`"checking"`, `"success"`, `"no_checks"`, `"pending_timeout"`,
   `"interrupted"`, `"exhausted"`, `"error"`) with a single enum. Used in
   `_ci_fix_loop`, `_format_ci_fix_message`, and metadata serialization.

3. **Pre-lowercase boilerplate prefixes** in `pr_description.py` — Added
   `_BOILERPLATE_PREFIXES_LOWER` pre-computed tuple to avoid repeated `.lower()`
   calls inside the hot `_is_boilerplate_line()` loop.

4. **`_LANGCHAIN_STREAM_EVENT` constant** in `langgraph.py` — Extracted the
   duplicated `"on_chat_model_stream"` magic string into a shared module-level
   constant, imported by `iterative.py`.

## Tasks

- [x] Create `CIConclusion(StrEnum)` with 5 members plus
  `CI_CONCLUSIONS_IN_PROGRESS` and `_CI_RUN_FAILURE_CONCLUSIONS` frozensets
- [x] Replace 5 hardcoded conclusion strings in `github.py` `get_check_runs()`
- [x] Create `CIFixStatus(StrEnum)` with 7 members in `cli/base.py`
- [x] Replace 10 hardcoded CI fix status strings in `_ci_fix_loop`,
  `_poll_ci_checks`, `_build_ci_fix_prompt`, `_format_ci_fix_message`
- [x] Add `_BOILERPLATE_PREFIXES_LOWER` pre-lowercased tuple in `pr_description.py`
- [x] Extract `_LANGCHAIN_STREAM_EVENT` constant in `langgraph.py`, import in
  `iterative.py`
- [x] Add 36 tests in `tests/test_v209_ci_enums_boilerplate_stream_event.py`
- [x] Update `test_v177` LangGraph `__all__` test for new export
- [x] All quality gates pass: ruff check, ruff format, ty check, pytest

## Completion criteria

- All tasks implemented with tests
- `ruff check`, `ruff format`, `ty check`, `pytest` all pass
- 5073 passed, 216 skipped
