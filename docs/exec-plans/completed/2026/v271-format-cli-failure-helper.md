# v271 — Extract `_format_cli_failure()` helper for CLI auth/failure messages

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17
**Tests:** 24 new (6278 passed, 273 skipped)

## Objective

Extract a `_format_cli_failure()` module-level function in `cli/base.py` to
eliminate the duplicated auth-detection + message-formatting pattern across
3 CLI hand implementations (codex, claude, opencode). Each had a ~12-line
static method that called `_detect_auth_failure`, formatted an auth message
with `_DOCKER_ENV_HINT_TEMPLATE`, or returned a generic failure line.

Gemini excluded — it has an extra model-not-found branch between auth and
generic failure that makes the helper less clean to apply.

## Tasks

- [x] Add `_format_cli_failure()` to `cli/base.py` with parameters for
      `backend_name`, `return_code`, `output`, `env_var_hint`,
      `auth_guidance`, `extra_tokens`
- [x] Add to `__all__` in `cli/base.py`
- [x] Simplify `CodexCLIHand._build_codex_failure_message` → delegate
- [x] Simplify `ClaudeCodeHand._build_claude_failure_message` → delegate
- [x] Simplify `OpenCodeCLIHand._build_opencode_failure_message` → delegate
- [x] Remove now-unused `_detect_auth_failure` / `_DOCKER_ENV_HINT_TEMPLATE`
      imports from codex.py, claude.py, opencode.py
- [x] Add 24 tests for `_format_cli_failure`
- [x] Update existing tests (v166, v193, v201, v203) that asserted direct
      `_detect_auth_failure` / `_DOCKER_ENV_HINT_TEMPLATE` usage
- [x] Run full test suite — 6278 passed, 273 skipped
- [x] Update docs

## Completion criteria

- 3 static method bodies (~36 lines) collapsed to 3 one-liner delegations
- `_format_cli_failure` is the single source of auth-failure message formatting
- All existing tests pass (static methods kept as thin wrappers)
- New tests cover `_format_cli_failure` directly
