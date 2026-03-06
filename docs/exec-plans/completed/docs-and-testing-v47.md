# Execution Plan: Docs and Testing v47

**Status:** Completed
**Created:** 2026-03-06
**Completed:** 2026-03-06
**Goal:** Fix frontend test failures, expand frontend test coverage, and document dead code paths.

---

## Tasks

### Phase 1: Fix frontend localStorage.clear test failures

- [x] Diagnose jsdom `window.localStorage.clear is not a function` error
- [x] Add localStorage polyfill to `frontend/src/test/setup.ts`
- [x] All 3 previously-failing task history tests now pass

### Phase 2: Expand frontend test coverage

- [x] Add `apiUrl` tests (path-only when API_BASE is empty)
- [x] Add `isTerminalTaskStatus` tests (terminal/non-terminal/whitespace-padded)
- [x] Add `parseError` edge cases (JSON without detail field, empty body -> HTTP status)
- [x] Add `statusTone` additional coverage (REVOKED, STARTED, PROGRESS, SUBMITTING)
- [x] Frontend tests: 14 -> 20 (all passing)

### Phase 3: Dead code documentation

- [x] Document iterative.py lines 830, 858 dead code in tech-debt-tracker
- [x] Document codex.py line 62 dead code in tech-debt-tracker
- [x] Note frontend localStorage polyfill in tech-debt-tracker

### Phase 4: Documentation updates

- [x] Update QUALITY_SCORE.md with frontend coverage entry
- [x] Update docs/PLANS.md with v47 entry
- [x] Update tech-debt-tracker with new items

### Phase 5: Validation

- [x] Frontend tests pass (20 passed)
- [x] Backend tests pass (1440 passed)
- [x] Lint and format clean
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-5 tasks checked off
- `npx vitest run` passes (20 tests)
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
