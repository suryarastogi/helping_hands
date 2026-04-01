# v347 — Coverage Gap Closure & PrefixEmitter Tests

**Status:** Completed
**Created:** 2026-04-01
**Completed:** 2026-04-01

## Context

Coverage was at 74.73%, just below the 75.0% CI threshold. Several small
modules had 1–12 uncovered lines that were straightforward to test. The
`_LinePrefixEmitter` helper class in `cli/base.py` had zero tests despite
being a self-contained async utility used by all CLI hands.

## Tasks

- [x] Add `_LinePrefixEmitter` tests (`cli/base.py` lines 311–328)
- [x] Add `opencode.py` `_pr_description_cmd` test (lines 35–37)
- [x] Add `devin.py` `_pr_description_cmd` and `_pr_description_prompt_as_arg` tests (lines 38–40, 44)
- [x] Add `github.py` `update_pr` tests (lines 542–549)
- [x] Verify coverage ≥ 75% and update docs

## Completion criteria

All met:
- All 19 new tests pass (6587 total, 0 failures)
- Overall coverage 74.73% → 75.20% (CI gate passes)
- `cli/base.py` branch partials reduced (2 → 1)
- `opencode.py` 90% → 95%
- `devin.py` 92% → 96%
- `github.py` 98% → 98% (update_pr lines now covered)
- 19 new tests added
- INTENT.md, PLANS.md updated

## New tests

| Module | Tests | What's covered |
|---|---|---|
| `_LinePrefixEmitter` | 10 | Line buffering, prefix injection, blank-line passthrough, double-prefix avoidance, flush with/without prefix, empty/whitespace buffer |
| `opencode.py` | 2 | `_pr_description_cmd` on-PATH and missing paths |
| `devin.py` | 3 | `_pr_description_cmd` on-PATH/missing, `_pr_description_prompt_as_arg` |
| `github.py` | 4 | `update_pr` both-None early return, title-only, body-only, both |
