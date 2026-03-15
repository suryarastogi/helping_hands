# v194 — Add _native_cli_auth_env_names() to GeminiCLIHand and GooseCLIHand

**Status:** completed
**Created:** 2026-03-15
**Branch:** helping-hands/claudecodecli-bfc17b62

## Goal

Two CLI hand subclasses (`GeminiCLIHand`, `GooseCLIHand`) are missing
`_native_cli_auth_env_names()` overrides. The base class returns an empty
tuple, which means `_describe_auth()` and `_effective_container_env_names()`
cannot properly detect or filter auth env vars for these backends.

`ClaudeCodeHand` and `CodexCLIHand` already override this method.
`OpenCodeCLIHand` uses session-based auth (`opencode auth login`), so the
empty-tuple default is correct.

## Tasks

- [x] Add `_native_cli_auth_env_names()` to `GeminiCLIHand` → `("GEMINI_API_KEY",)`
- [x] Add `_native_cli_auth_env_names()` to `GooseCLIHand` → all known provider API key env vars
- [x] Write tests for both implementations (return values, type, consistency with _describe_auth)
- [x] Run quality checks (ruff, ty, pytest)
- [x] Update Week-12 log entry and PLANS.md

## Completion criteria

- All 4 CLI hands with known auth env vars override `_native_cli_auth_env_names()`
- Tests verify return values and tuple type
- All quality gates pass
- Test count increases
