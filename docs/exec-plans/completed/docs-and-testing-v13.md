# Execution Plan: Docs and Testing v13

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Add unit tests for app.py pure helper functions (task extraction, backend parsing, Flower config) and CLI base.py static helpers (CI fix prompt, PR status formatting, edit detection); update QUALITY_SCORE.md.

---

## Tasks

### Phase 1: App.py helper function tests

- [x] `_parse_backend` — valid backends, invalid backend raises ValueError
- [x] `_task_state_priority` — known states return expected priorities, unknown returns 0
- [x] `_normalize_task_status` — whitespace trimming, uppercasing, None/empty defaults
- [x] `_extract_task_id` — direct keys, nested request payload, missing returns None
- [x] `_extract_task_name` — direct keys, nested request payload, missing returns None
- [x] `_extract_task_kwargs` — dict passthrough, string JSON, string literal_eval, nested request, empty
- [x] `_coerce_optional_str` — non-string returns None, empty/whitespace returns None, valid string trimmed
- [x] `_parse_task_kwargs_str` — valid JSON, valid Python literal, invalid string, empty
- [x] `_is_helping_hands_task` — matching name, non-matching name, missing name returns True
- [x] `_upsert_current_task` — insert new, merge with higher priority status, merge sources
- [x] `_flower_timeout_seconds` — env set, env invalid, env unset
- [x] `_flower_api_base_url` — env set with trailing slash, env unset

### Phase 2: CLI base.py static helper tests

- [x] `_build_ci_fix_prompt` — builds prompt with failed check details
- [x] `_format_ci_fix_message` — all status variants
- [x] `_format_pr_status_message` — all PR status variants
- [x] `_looks_like_edit_request` — positive and negative examples

### Phase 3: Validation

- [x] All tests pass (1005 passed)
- [x] Lint and format clean
- [x] Update `docs/QUALITY_SCORE.md` with new coverage notes
- [x] Move plan to completed, update `docs/PLANS.md`

---

## Completion criteria

- All Phase 1-3 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
