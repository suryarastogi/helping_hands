# v355 — Troubleshooting Guide & Docs Refresh

**Created:** 2026-04-04
**Status:** Active

## Goal

Create a user-facing troubleshooting guide (`docs/TROUBLESHOOTING.md`) covering
common issues surfaced by `helping-hands doctor` and known CLI failure modes.
Refresh stale metadata in `AGENTS.md`. Add doc structure tests to keep the
troubleshooting guide in sync with the codebase.

## Tasks

- [x] Create `docs/TROUBLESHOOTING.md` with sections for:
      - Environment setup issues (Python version, missing git/uv)
      - API key configuration
      - GitHub token issues
      - Backend-specific problems (CLI tool not found, Docker missing)
      - Common runtime errors (idle timeout, model not found, permission denied)
      - Server mode prerequisites
- [x] Update `AGENTS.md` last-updated date (2026-03-07 → 2026-04-04)
- [x] Add doc structure tests for TROUBLESHOOTING.md (12 tests in TestTroubleshootingMd)
- [x] Add TROUBLESHOOTING.md to docs/index.md
- [x] Update `docs/PLANS.md` to reference v355
- [x] Update `INTENT.md` with active intent
- [x] Fix pr_description.py line-too-long (line 532, 90 chars → split)
- [x] Move completed v354 plan from active/ to completed/2026/
- [x] Run pytest, ruff check, ruff format — all clean
      (6773 passed, 271 skipped, 75.35% coverage)

## Completion criteria

- `docs/TROUBLESHOOTING.md` exists with actionable solutions for ≥6 common issues ✓
  (11 issues covered across 6 sections)
- AGENTS.md date is current ✓ (2026-04-04)
- New doc structure tests pass ✓ (12 new tests in TestTroubleshootingMd)
- All existing tests still pass ✓ (6773 passed)
- ruff check + format clean ✓
