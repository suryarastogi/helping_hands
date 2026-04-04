# v347 — Fix Grill Test Failures & Week-14 Consolidation

**Created:** 2026-04-04
**Status:** Completed

## Problem

17 tests in `test_grill.py` fail with `ModuleNotFoundError: No module named 'celery'`
when the `server` extra is not installed. All other server-module tests use
`pytest.importorskip()` to guard optional-dependency imports; `test_grill.py` is the
only server test file missing this guard.

Additionally, the 2026-03-30 daily plans (v339–v346) have not been consolidated
into a Week-14 summary, and the recent README slim-down left doc structure tests
stale.

## Tasks

- [x] Add `pytest.importorskip("celery")` at module level in `test_grill.py`
- [x] Create `docs/exec-plans/completed/2026/Week-14.md`
- [x] Update `TestReadmeMdSections` to match slimmed README (remove `## Configuration`, `## Development`)
- [x] Update `TestReadmeSections.test_mentions_github_token` for slimmed README
- [x] Add missing docs to `docs/index.md` (`app-mode.md`, `backends.md`, `development.md`)
- [x] Update PLANS.md to reference active plan
- [x] Update INTENT.md
- [x] Run full test suite — 0 failures (6567 passed, 269 skipped)
- [x] Move plan to completed

## Completion criteria

- `uv run pytest` passes with 0 failures
- Week-14 consolidation file exists
- All doc structure tests pass
- Documentation updated
