## v146 — Commit message quality: truncation indicators and smart type inference

**Status:** Active
**Created:** 2026-03-12

## Goal

Two self-contained improvements to `pr_description.py` addressing the TODO.md item "commit message created by claudecodecli still mediocre":

1. **Add truncation indicators for prompt/summary context** — `_build_prompt()` and `_build_commit_message_prompt()` silently truncate `user_prompt` and `summary` using `[:_PROMPT_CONTEXT_LENGTH]` and `[:_*_TRUNCATION_LENGTH]` without any indicator. When text is cut mid-sentence, the AI receives incomplete context and may generate generic commit messages. Add truncation markers (matching `_truncate_diff()` pattern) to help the AI understand the context is truncated.

2. **Smart commit type inference in `_commit_message_from_prompt()`** — The fallback `_commit_message_from_prompt()` always hardcodes `"feat:"` prefix regardless of content. When the text describes a fix, refactor, or docs change, the prefix should match. Add keyword-based inference with `_COMMIT_TYPE_KEYWORDS` dict and word-boundary matching to select the appropriate conventional commit type.

## Tasks

- [x] Add `_truncate_text()` helper for prompt/summary truncation with indicator
- [x] Use `_truncate_text()` in `_build_prompt()` for user_prompt and summary
- [x] Use `_truncate_text()` in `_build_commit_message_prompt()` for user_prompt and summary
- [x] Add `_COMMIT_TYPE_KEYWORDS` dict and `_infer_commit_type()` helper with word-boundary matching
- [x] Use `_infer_commit_type()` in `_commit_message_from_prompt()` instead of hardcoded "feat:"
- [x] Add tests for `_truncate_text()` (8 tests: short/exact/long/strip/empty/whitespace/zero-limit/negative-limit)
- [x] Add tests for `_infer_commit_type()` (24 tests: all commit types, case insensitivity, priority, false positive guards)
- [x] Add tests for prompt builders with truncation indicators (7 tests: long/short prompt and summary)
- [x] Add tests for `_commit_message_from_prompt()` type inference (7 tests: fix/refactor/docs/test/feat/chore/perf)
- [x] Update existing tests for new type inference behavior (7 tests updated)
- [x] Run lint and tests — 3542 passing, 80 skipped
- [x] Update docs (PLANS.md, QUALITY_SCORE.md, Week-11)

## Completion criteria

- All new tests pass (48 new tests)
- `ruff check` and `ruff format` pass
- Docs updated with v146 notes
