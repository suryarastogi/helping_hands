# Execution Plan: Docs and Testing v40

**Status:** Completed
**Created:** 2026-03-06
**Completed:** 2026-03-06
**Goal:** Add DockerSandboxClaudeCodeHand `_invoke_backend`/`_run_two_phase` tests; CLI base `_invoke_backend` delegation and `_run_two_phase` skill catalog lifecycle tests; BasicAtomicHand.stream() delta-without-prefix and file-change/tool-result yield coverage; update DESIGN.md with two-phase lifecycle and IO loop patterns; update QUALITY_SCORE.md.

---

## Tasks

### Phase 1: DockerSandboxClaudeCodeHand integration method tests

- [x] `_invoke_backend` (wraps command with sandbox exec, uses stream-json emitter, returns result)
- [x] `_run_two_phase` (calls `_ensure_sandbox` before, `_remove_sandbox` after when cleanup enabled)
- [x] `_run_two_phase` (skips `_remove_sandbox` when cleanup disabled)

### Phase 2: CLI base `_invoke_backend` and `_run_two_phase` tests

- [x] `_invoke_backend` delegates to `_invoke_cli`
- [x] `_run_two_phase` calls `reset_interrupt`, `_stage_skill_catalog`, `_run_two_phase_inner`, `_cleanup_skill_catalog`
- [x] `_run_two_phase` cleans up skill catalog even on exception

### Phase 3: BasicAtomicHand.stream() gap coverage

- [x] Delta without prefix match (line 830/845/858 — response doesn't start with previous text)
- [x] File change yield (line 868 — `_apply_inline_edits` returns changed files)
- [x] Tool result yield (line 875 — `_execute_read_requests`/`_execute_tool_requests` return feedback)

### Phase 4: Documentation

- [x] Update DESIGN.md with two-phase CLI hand lifecycle and IO loop patterns
- [x] Update QUALITY_SCORE.md with new test entries

### Phase 5: Validation

- [x] All tests pass
- [x] Lint and format clean
- [x] Update docs/PLANS.md
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-5 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
