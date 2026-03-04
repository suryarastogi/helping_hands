# Execution Plan: Improve Docs and Testing v2

**Status:** Completed
**Created:** 2026-03-04
**Completed:** 2026-03-04
**Goal:** Address tech debt items TD-001, TD-002, TD-003 from the tracker — add ScheduleManager unit tests, registry parser edge-case tests, and AI provider error-path tests.

---

## Phase 1: ScheduleManager Unit Tests (TD-001)

- [x] Test ScheduleManager CRUD operations with mocked Redis/RedBeat
- [x] Test enable/disable toggling
- [x] Test record_run metadata updates
- [x] Test trigger_now delegation
- [x] Test error paths (duplicate create, update nonexistent, delete nonexistent)
- [x] Test next_run_time utility function

## Phase 2: Registry Parser Edge Cases (TD-002)

- [x] Test `_parse_str_list` — None input, non-list, non-string items
- [x] Test `_parse_positive_int` — bool rejection, zero/negative, missing key
- [x] Test `_parse_optional_str` — whitespace-only, empty string, non-string
- [x] Test `normalize_tool_selection` — tuple input, non-string items, underscores
- [x] Test runner wrapper validation errors (empty code, missing script_path, etc.)

## Phase 3: AI Provider Error Paths (TD-003)

- [x] Test lazy inner client construction via `_build_inner`
- [x] Test `complete()` with explicit model override
- [x] Test `acomplete()` async wrapper
- [x] Test `normalize_messages` edge cases (empty content, missing role)

---

## Completion Criteria

Move to `completed/` when all phases are done and tests pass.
