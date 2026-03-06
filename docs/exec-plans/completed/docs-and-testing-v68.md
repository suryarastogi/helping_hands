# Execution Plan: Docs and Testing v68

**Status:** Completed
**Created:** 2026-03-06
**Goal:** Add scheduling-system design doc; update docs/index.md; add shared make_fake_module conftest fixture; add conftest self-tests.

---

## Tasks

### Phase 1: Documentation improvements

- [x] Add `scheduling-system.md` design doc (RedBeat, ScheduleManager CRUD, cron presets, trigger-now, dual storage model)
- [x] Update design-docs/index.md with new doc
- [x] Update docs/index.md design-docs listing to include repo-indexing and scheduling-system

### Phase 2: Test infrastructure

- [x] Add `make_fake_module` factory fixture to conftest.py (reduce repeated ModuleType + MagicMock setup across 4+ provider test files)
- [x] Add conftest self-tests for new fixture in test_conftest_fixtures.py (5 tests)

### Phase 3: Finalize

- [x] All tests pass (1545 passed, 6 skipped)
- [x] Update testing-methodology.md stats
- [x] Update PLANS.md
- [x] Move plan to completed

---

## Completion criteria

- Scheduling-system design doc captures RedBeat, CRUD, cron presets, trigger-now patterns
- docs/index.md design-docs description includes repo-indexing and scheduling-system
- Shared make_fake_module fixture available for provider tests
- All tests pass
- PLANS.md updated
