# v347 — Coverage Gap Closure & Weekly Consolidation

**Created:** 2026-04-01
**Status:** Complete

## Goal

Close remaining testable coverage gaps in CLI hand modules and GitHub client
to bring overall coverage back above the 75% CI gate (currently 74.73%).

## Tasks

- [x] OpenCode `_pr_description_cmd` tests (lines 35-37)
- [x] Devin `_pr_description_cmd` + `_pr_description_prompt_as_arg` tests (lines 38-40, 44)
- [x] `_LinePrefixEmitter` tests for `__call__` and `flush` (cli/base.py lines 311-328)
- [x] `update_pr` tests (github.py lines 542-549)
- [x] Update PLANS.md, INTENT.md with results

## Completion criteria

- [x] `uv run pytest -v` passes with coverage ≥ 75%
- [x] All new tests are semantically meaningful
- [x] Docs updated

## Results

- **21 new tests**: 2 OpenCode, 3 Devin, 10 `_LinePrefixEmitter`, 6 `update_pr`
- **Coverage**: 74.73% → 75.20%
- **cli/base.py**: 98% → 99% (lines 311-328 now covered)
- **opencode.py**: 90% → 100% (`_pr_description_cmd` covered)
- **devin.py**: 92% → 100% (`_pr_description_cmd` + `_pr_description_prompt_as_arg` covered)
- **github.py**: 98% (new `update_pr` method covered)
- **6589 tests passed**, 0 failures
