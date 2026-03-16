# v230 — Claude CLI model filter, auth description, exception narrowing

**Created:** 2026-03-16
**Status:** Completed

## Goal

Three self-contained improvements to the Claude Code CLI hand for consistency
and robustness:

1. **Expand incompatible-model filter** — `_resolve_cli_model()` now rejects
   both `gpt-*` and `openai/*` prefixed models (after base-class strip).
2. **Add `_describe_auth()` override** — Consistent with Gemini and Goose,
   Claude now reports `ANTHROPIC_API_KEY` presence.
3. **Narrow exception handling** — `_skip_permissions_enabled()` catches
   `(ValueError, OSError)` instead of bare `Exception`.

## Tasks

- [x] Create this plan
- [x] Expand `_resolve_cli_model()` to also filter `openai/` models
- [x] Add `_describe_auth()` to `ClaudeCodeHand`
- [x] Narrow `except Exception` → `except (ValueError, OSError)`
- [x] Add tests for all three changes
- [x] Run lint, format, type check, pytest
- [x] Update docs

## Completion criteria

- All changes have full branch coverage tests
- Lint, format, type check pass
- Full test suite passes with no regressions

## Files changed

- `src/helping_hands/lib/hands/v1/hand/cli/claude.py`
- `tests/test_v230_claude_cli_model_auth_exceptions.py`
- `tests/test_v217_provider_consistency.py` (updated warning assertion)
