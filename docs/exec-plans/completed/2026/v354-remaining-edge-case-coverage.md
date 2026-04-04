# v354 — Remaining Edge Case Coverage

**Created:** 2026-04-04
**Status:** Active

## Goal

Close the last <2% coverage gaps in high-use modules: `github.py` (`update_pr`),
`cli/base.py` (`_LinePrefixEmitter`), `cli/claude.py` (`_summarize_tool` Skill
branch), and `cli/goose.py` (`_pr_description_cmd` Google/Gemini path). These
are all in the critical path for output correctness and PR workflow automation.

## Tasks

- [x] Move completed v353 plan from `active/` to `completed/2026/`
- [x] Add `update_pr` tests: positive-int validation, both-None early return,
      title-only, body-only, both-provided (5 tests)
- [x] Add `_LinePrefixEmitter` tests: complete line, blank line, already-prefixed,
      multi-line chunk, incomplete buffering, flush with content, flush empty,
      flush already-prefixed (8 tests)
- [x] Add `_summarize_tool` Skill branch tests: skill present, skill empty (2 tests)
- [x] Add `_pr_description_cmd` Google/Gemini path tests: google with gemini binary,
      google without gemini binary (2 tests)
- [x] Run pytest, ruff check, ruff format — all clean
      (6760 passed, 271 skipped, 75.35% coverage)
- [x] Update INTENT.md, PLANS.md

## Completion criteria

- github.py coverage: 98% → 100% ✓ (no longer listed in report)
- cli/base.py coverage: 98% → 99%+ ✓ (only branch 1284→1293 remains)
- cli/claude.py coverage: 99% → 100% ✓ (no longer listed in report)
- cli/goose.py coverage: 99% → 100% ✓ (no longer listed in report)
- All new tests pass ✓ (17 new tests, 6760 total pass)
- ruff check + format clean ✓
