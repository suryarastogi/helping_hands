# Execution Plan: Docs and Testing v25

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Add missing unit tests for Gemini and Codex CLI hand helpers; update QUALITY_SCORE.md.

---

## Tasks

### Phase 1: Gemini CLI hand helper tests

- [x] `_describe_auth` — key set vs not set vs empty
- [x] `_pr_description_cmd` — gemini found vs not found
- [x] `_command_not_found_message` — includes command name and env var

### Phase 2: Codex CLI hand helper tests

- [x] `_command_not_found_message` — includes command name and env var
- [x] `_native_cli_auth_env_names` — returns OPENAI_API_KEY
- [x] `_apply_codex_exec_sandbox_defaults` — empty/whitespace env override falls back to auto

### Phase 3: Validation

- [x] All tests pass (1130 passed, 6 skipped)
- [x] Lint and format clean
- [x] Update `docs/QUALITY_SCORE.md` with new coverage notes
- [x] Update `docs/PLANS.md`
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-3 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
