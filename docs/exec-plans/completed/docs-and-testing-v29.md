# Execution Plan: Docs and Testing v29

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Increase CLI base.py coverage (91% -> 93%+) with skill catalog, container wrapping, and task prompt branch coverage tests; add Hand base.py branch tests for `_finalize_repo_pr` edge paths.

---

## Tasks

### Phase 1: CLI base.py unit tests

- [x] `_stage_skill_catalog` — stages skills to temp directory (mocked)
- [x] `_cleanup_skill_catalog` — cleans up temp directory
- [x] `_cleanup_skill_catalog` — no-op when no catalog dir set
- [x] `_wrap_container_if_enabled` — container disabled returns cmd unchanged
- [x] `_wrap_container_if_enabled` — docker not found raises RuntimeError
- [x] `_wrap_container_if_enabled` — builds docker cmd with env vars
- [x] `_build_task_prompt` — includes tool section when tools enabled
- [x] `_build_task_prompt` — includes skill section when skills enabled
- [x] `_build_task_prompt` — omits tool/skill sections when formatters return empty

### Phase 2: Hand base.py branch tests

- [x] `_finalize_repo_pr` — repo_dir not a directory returns no_repo
- [x] `_finalize_repo_pr` — not a git repo returns not_git_repo
- [x] `_run_git_read` — successful command returns stripped stdout

### Phase 3: Validation

- [x] All tests pass
- [x] Lint and format clean
- [x] Update `docs/QUALITY_SCORE.md` with new coverage notes
- [x] Update `docs/PLANS.md`
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-3 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
