## v139 — Extract hardcoded magic numbers in claude.py, pr_description.py, and CLI failure output

**Status:** Active
**Created:** 2026-03-12

## Goal

Four self-contained improvements continuing the v135-v138 constant extraction pattern:

1. **Claude CLI preview truncation constants** (`cli/claude.py`) — Extract hardcoded text preview (200), tool result preview (150), and command/prompt preview (80) truncation limits to module-level constants.

2. **PR description truncation constants** (`pr_description.py`) — Extract hardcoded summary truncation (2000/1000), user prompt context (500), error output tail (300/500), and commit message length (72) limits to module-level constants.

3. **DRY failure output tail constant** (`cli/claude.py`, `cli/codex.py`, `cli/gemini.py`, `cli/opencode.py`) — The `output.strip()[-2000:]` failure message tail truncation is duplicated identically in 4 CLI hands. Extract to a module-level constant in each file (modules don't import each other's internals per architecture rules).

4. **Fix hardcoded file list limit** (`cli/base.py`) — Line 353 uses hardcoded `[:200]` instead of the existing `_FILE_LIST_PREVIEW_LIMIT` constant from `base.py`.

## Tasks

- [x] Extract `_TEXT_PREVIEW_MAX_LENGTH`, `_TOOL_RESULT_PREVIEW_MAX_LENGTH`, `_COMMAND_PREVIEW_MAX_LENGTH` in `cli/claude.py`
- [x] Extract `_FAILURE_OUTPUT_TAIL_LENGTH` in `cli/claude.py`, `cli/codex.py`, `cli/gemini.py`, `cli/opencode.py`
- [x] Extract `_PR_SUMMARY_TRUNCATION_LENGTH`, `_COMMIT_SUMMARY_TRUNCATION_LENGTH`, `_PROMPT_CONTEXT_LENGTH`, `_PR_ERROR_TAIL_LENGTH`, `_COMMIT_ERROR_TAIL_LENGTH`, `_COMMIT_MSG_MAX_LENGTH` in `pr_description.py`
- [x] Import and use `_FILE_LIST_PREVIEW_LIMIT` from `base.py` in `cli/base.py`
- [x] Add tests for constant values and usage (29 tests: value, type, sign, cross-module sync invariants)
- [x] Run lint and tests — 3436 passing, 37 skipped
- [x] Update docs (PLANS.md, QUALITY_SCORE.md, Week-11)

## Completion criteria

- All new tests pass
- `ruff check` and `ruff format` pass
- Docs updated with v139 notes
