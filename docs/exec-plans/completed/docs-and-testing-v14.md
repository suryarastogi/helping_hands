# Execution Plan: Docs and Testing v14

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Add unit tests for cli/main.py pure helper functions and missing backend paths; update ARCHITECTURE.md with current module inventory; update QUALITY_SCORE.md.

---

## Tasks

### Phase 1: cli/main.py static helper tests

- [x] `_github_clone_url` -- with token, without token, GH_TOKEN fallback, empty token
- [x] `_git_noninteractive_env` -- sets GIT_TERMINAL_PROMPT and GCM_INTERACTIVE, preserves env
- [x] `_redact_sensitive` -- redacts token from URL, passes non-matching text, empty string
- [x] `_repo_tmp_dir` -- env set returns Path, env unset returns None, empty string, nested dirs

### Phase 2: cli/main.py missing backend/error path tests

- [x] `opencodecli` backend dispatches to OpenCodeCLIHand
- [x] `model_not_found` error path exits with helpful message
- [x] Invalid `--tools` flag exits with error

### Phase 3: ARCHITECTURE.md update

- [x] Refresh key file paths table to reflect all current source files
- [x] Add model_provider, pr_description, default_prompts, command, web, skills, celery_app, schedules, task_result, placeholders

### Phase 4: Validation

- [x] All tests pass (845 passed)
- [x] Lint and format clean
- [x] Update `docs/QUALITY_SCORE.md` with new coverage notes
- [x] Move plan to completed, update `docs/PLANS.md`

---

## Completion criteria

- All Phase 1-4 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
