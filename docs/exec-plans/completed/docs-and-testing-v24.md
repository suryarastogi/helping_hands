# Execution Plan: Docs and Testing v24

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Add unit tests for CLI base.py CI fix loop and run/stream wrappers; web.py helper coverage gaps; update QUALITY_SCORE.md.

---

## Tasks

### Phase 1: CLI base.py CI fix loop tests

- [x] `_ci_fix_loop` — fix_ci disabled returns metadata unchanged
- [x] `_ci_fix_loop` — PR status not created/updated returns early
- [x] `_ci_fix_loop` — missing pr_commit/pr_branch returns early
- [x] `_ci_fix_loop` — no GitHub repo returns early
- [x] `_ci_fix_loop` — CI passes (success path)
- [x] `_ci_fix_loop` — no_checks path
- [x] `_ci_fix_loop` — pending timeout path
- [x] `_ci_fix_loop` — CI fails, fix produces changes, pushed
- [x] `_ci_fix_loop` — CI fails, fix produces no changes
- [x] `_ci_fix_loop` — interrupted during loop
- [x] `_ci_fix_loop` — retries exhausted
- [x] `_ci_fix_loop` — exception in loop sets error status
- [x] `_poll_ci_checks` — returns immediately on non-pending result
- [x] `_poll_ci_checks` — polls until deadline

### Phase 2: CLI base.py run/stream wrapper tests

- [x] `run()` — collects output and finalizes, no CI fix
- [x] `run()` — with CI fix enabled triggers fix loop
- [x] `run()` — no CI fix when PR not created
- [x] `stream()` — yields chunks and finalizes with PR status

### Phase 3: web.py helper coverage

- [x] `_extract_related_topics` — text+url extraction, recursive Topics, non-dict/missing/empty skips
- [x] `_require_http_url` — whitespace-only, no-scheme
- [x] `_strip_html` — noscript removal, blank line collapsing
- [x] `search_web` — invalid max_results/timeout_s, unexpected format, dedup, empty URLs, max_results cap
- [x] `browse_url` — non-HTML content, invalid max_chars/timeout_s, HTML-by-body-detection

### Phase 4: Validation

- [x] All tests pass (1120 passed, 6 skipped)
- [x] Lint and format clean
- [x] Update `docs/QUALITY_SCORE.md` with new coverage notes
- [x] Update `docs/PLANS.md`
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-4 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
