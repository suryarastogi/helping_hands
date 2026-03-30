# v347 — Coverage Threshold Fix & CLI Hand PR Description Tests

**Status:** completed
**Date:** 2026-03-30

## Problem

Coverage dropped to 74.99%, failing the 75% CI threshold. Three modules
had easy-to-close gaps: `opencode.py` (90%), `devin.py` (92%), and
`github.py` `update_pr` method (lines 542-549 uncovered).

## Changes

### OpenCode CLI Hand (`opencode.py` 90% → 100%)
- `_pr_description_cmd`: test when `opencode` is on `$PATH` (returns
  `["opencode", "run"]`) and when missing (returns `None`).

### Devin CLI Hand (`devin.py` 92% → 100%)
- `_pr_description_cmd`: test when `devin` is on `$PATH` (returns
  `["devin", "-p", "--"]`) and when missing (returns `None`).
- `_pr_description_prompt_as_arg`: test returns `True`.

### GitHub Client (`github.py` 98% → 99%)
- `update_pr`: title-only, body-only, title+body, both-None early return,
  and invalid PR number validation. Mocked `github.NotSet` import to
  avoid PyGithub dependency in base test env.

## Results

- **10 new tests** (2 opencode, 3 devin, 5 github)
- **6659 tests passed**, 275 skipped
- **Coverage: 75.21%** (up from 74.99%)
- CI threshold restored
