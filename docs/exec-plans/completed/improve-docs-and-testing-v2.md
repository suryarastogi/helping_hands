# Execution Plan: Improve Docs and Testing (v2)

**Status:** Completed
**Created:** 2026-03-04
**Completed:** 2026-03-04
**Goal:** Fill remaining docs structure gaps and close medium-priority testing debt from tech-debt-tracker.

---

## Phase 1: Documentation Structure Completion

- [x] Create `docs/exec-plans/active/` directory
- [x] Create `docs/references/` directory with placeholder index
- [x] Create `docs/generated/` directory
- [x] Create `docs/FRONTEND.md` — frontend architecture and conventions
- [x] Create `docs/PLANS.md` — how execution plans work
- [x] Create `docs/PRODUCT_SENSE.md` — product thinking guidelines
- [x] Create `docs/design-docs/core-beliefs.md` — extracted from DESIGN.md

## Phase 2: Testing — ScheduleManager (TD-001)

- [x] Add ScheduleManager unit tests with mocked Redis/RedBeat
- [x] Cover CRUD operations, enable/disable, record_run, trigger_now
- [x] Cover edge cases: duplicate ID, missing schedule, already enabled/disabled

## Phase 3: Testing — Registry Edge Cases (TD-002)

- [x] Add parser validator edge cases (_parse_str_list, _parse_positive_int, _parse_optional_str)
- [x] Add normalize_tool_selection edge cases (mixed types, underscores, empty strings)
- [x] Add validate_tool_category_names with multiple unknown tools

## Phase 4: Tracking Updates

- [x] Update `docs/QUALITY_SCORE.md` with new coverage
- [x] Update `docs/exec-plans/tech-debt-tracker.md` — resolve TD-001, TD-002

---

## Completion Criteria

Move to `completed/` when all phases are done and tests pass.
