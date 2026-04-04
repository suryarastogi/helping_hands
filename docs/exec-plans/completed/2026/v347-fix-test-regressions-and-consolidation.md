# v347 — Fix Test Regressions & Weekly Consolidation

**Status:** Completed
**Created:** 2026-04-04

## Objective

Fix 17 test failures introduced by the README slim-down (c7601f0) and missing
celery skip guards, then consolidate March 30 daily plans into a weekly summary.

## Tasks

- [x] Update `docs/index.md` to reference `app-mode.md`, `development.md`, `backends.md`
- [x] Update `TestReadmeMdSections` to match slimmed README (drop `## Configuration` / `## Development`)
- [x] Add `GITHUB_TOKEN` mention to README Quick Start for `test_mentions_github_token`
- [x] Add `pytest.importorskip("celery")` guard to `test_grill.py`
- [x] Reference v347 in `PLANS.md`
- [x] Create `Week-14.md` consolidation (Mar 30 – Apr 5)
- [x] Update `INTENT.md` with completion

## Completion criteria

- `uv run pytest -v` passes with 0 failures (grill tests skip when celery absent)
- All docs structure tests green
- Weekly consolidation complete
