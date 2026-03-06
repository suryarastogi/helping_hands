# Execution Plan: Docs and Testing v53

**Status:** Completed
**Created:** 2026-03-06
**Completed:** 2026-03-06
**Goal:** Close branch coverage gaps in core modules (base.py, registry.py, web.py); update docs and tech-debt-tracker.

---

## Tasks

### Phase 1: Hand base.py branch coverage

- [x] `_run_precommit_checks_and_fixes`: test with stdout-only (no stderr) so line 243->245 false branch is covered
- [x] `_finalize_repo_pr`: test with `pr_number` set to exercise `_push_to_existing_pr` return (line 560)
- [x] `_finalize_repo_pr`: test where `repo_obj.default_branch` is falsy/empty (line 597->602 false branch)

### Phase 2: Registry and web branch coverage

- [x] `normalize_tool_selection`: test with non-string element in list input (line 244 ValueError)
- [x] `format_tool_instructions_for_cli`: test with tool that has no guidance entry (line 372->370 skip)
- [x] `search_web`: test where DuckDuckGo `RelatedTopics` is not a list (line 163->166 skip)

### Phase 3: Goose CLI branch coverage

- [x] Confirmed goose.py line 135 is dead code (outer `.strip()` prevents reaching it); documented in tech-debt-tracker

### Phase 4: Documentation updates

- [x] Update docs/PLANS.md with v53 entry
- [x] Update QUALITY_SCORE.md with new coverage entries (base.py, registry.py 99%, web.py 99%)
- [x] Update tech-debt-tracker with goose.py line 135 dead code item

### Phase 5: Validation

- [x] All backend tests pass (1470 passed, 6 skipped)
- [x] Ruff lint and format pass
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-5 tasks checked off
- `uv run pytest -v` passes (1470 tests)
- `uv run ruff check . && uv run ruff format --check .` passes
