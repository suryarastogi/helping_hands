# Execution Plan: Docs and Testing v2

**Status:** Completed
**Created:** 2026-03-04
**Completed:** 2026-03-04
**Goal:** Fill documentation gaps (product specs, design docs) and add targeted tests for untested utility methods and the OpenCode CLI hand.

---

## Tasks

### Phase 1: Documentation improvements

- [x] Fix stale `docs/PLANS.md` — updated to reflect completed plan and this active plan
- [x] Add `docs/product-specs/new-user-onboarding.md` — first real product spec
  covering quick-start flow, examples directory, and `doctor` command
- [x] Add `docs/design-docs/hand-abstraction.md` — documents Hand class hierarchy,
  extension model, two-phase CLI pattern, and design alternatives
- [x] Update `docs/design-docs/index.md` and `docs/product-specs/index.md` with new entries

### Phase 2: Testing improvements

- [x] Add 18 unit tests for `_TwoPhaseCLIHand` utility methods:
  `_truncate_summary` (4 tests), `_is_truthy` (3 tests),
  `_inject_prompt_argument` (5 tests), `_float_env` (4 tests),
  `_looks_like_edit_request` (2 tests)
- [x] Add 8 tests for `OpenCodeCLIHand` — failure messages (3 tests),
  model resolution (3 tests), command rendering (1 test),
  command not found message (1 test)
- [x] Verify all tests pass: 385 passed, 2 skipped
- [x] Verify lint clean: `uv run ruff check .` all checks passed

---

## Completion criteria

- All Phase 1 and Phase 2 tasks checked off
- `uv run pytest --ignore=tests/test_schedules.py -v` passes (385 passed)
- `uv run ruff check .` passes
