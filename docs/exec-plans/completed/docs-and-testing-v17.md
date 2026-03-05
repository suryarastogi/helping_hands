# Execution Plan: Docs and Testing v17

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Add unit tests for CLI base.py undertested helper methods (_resolve_cli_model, _inject_prompt_argument, _normalize_base_command, _build_failure_message, _describe_auth, _effective_container_env_names, _build_subprocess_env, _interrupted_pr_metadata); Anthropic and LiteLLM _complete_impl extra kwargs tests; update QUALITY_SCORE.md.

---

## Tasks

### Phase 1: CLI base.py helper tests

- [x] `_resolve_cli_model` -- bare model, "default", provider/model format, empty
- [x] `_inject_prompt_argument` -- -p flag, --prompt flag, --prompt= format, -p= format, no flag
- [x] `_normalize_base_command` -- single token with defaults, multi-token passthrough
- [x] `_build_failure_message` -- formats exit code and truncated output
- [x] `_describe_auth` -- native CLI auth, env var set, no env var, no native names
- [x] `_effective_container_env_names` -- filters blocked names when native auth enabled
- [x] `_build_subprocess_env` -- strips native auth env vars when enabled
- [x] `_interrupted_pr_metadata` -- returns correct dict shape

### Phase 2: Provider _complete_impl extra kwargs

- [x] Anthropic `_complete_impl` -- extra kwargs forwarded to inner.messages.create
- [x] LiteLLM `_complete_impl` -- extra kwargs forwarded to inner.completion

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
