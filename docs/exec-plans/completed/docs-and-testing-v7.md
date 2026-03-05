# Execution Plan: Docs and Testing v7

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Add dedicated test suites for all untested CLI hand backends (Claude, Codex, Gemini, OpenCode) covering static/pure helper methods; update DESIGN.md with CLI-specific patterns.

---

## Tasks

### Phase 1: CLI hand test coverage

- [x] Claude CLI hand tests: `_build_claude_failure_message`, `_resolve_cli_model`,
  `_skip_permissions_enabled`, `_apply_backend_defaults`,
  `_retry_command_after_failure`, `_no_change_error_after_retries`,
  `_fallback_command_when_not_found`, `_inject_output_format`,
  `_StreamJsonEmitter` async processing (assistant/user/result events, flush, result_text)
- [x] Codex CLI hand tests: `_build_codex_failure_message`,
  `_normalize_base_command`, `_apply_codex_exec_sandbox_defaults`,
  `_auto_sandbox_mode`, `_skip_git_repo_check_enabled`,
  `_apply_codex_exec_git_repo_check_defaults`
- [x] Gemini CLI hand tests: `_looks_like_model_not_found`,
  `_extract_unavailable_model`, `_strip_model_args`,
  `_has_approval_mode_flag`, `_apply_backend_defaults`,
  `_build_gemini_failure_message`, `_retry_command_after_failure`
- [x] OpenCode CLI hand tests: `_build_opencode_failure_message`,
  `_resolve_cli_model`

### Phase 2: Documentation improvements

- [x] Update `docs/DESIGN.md` with CLI hand backend-specific patterns
  (per-backend auth, retry strategies, output format injection, sandbox modes)

### Phase 3: Validation

- [x] All tests pass
- [x] Lint and format clean
- [x] Move plan to completed, update `docs/PLANS.md`

---

## Completion criteria

- All Phase 1-3 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
