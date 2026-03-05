# Execution Plan: Docs and Testing v27

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Goal:** Increase test coverage for DockerSandboxClaudeCodeHand (19% -> 91%) and meta/skills edge cases (94% -> 98%).

---

## Tasks

### Phase 1: DockerSandboxClaudeCodeHand tests (19% -> 91%)

- [x] `__init__` — sandbox state initialized
- [x] `_resolve_sandbox_name` — env var override
- [x] `_resolve_sandbox_name` — env var strips whitespace
- [x] `_resolve_sandbox_name` — auto-generated from repo name
- [x] `_resolve_sandbox_name` — caching (second call returns same)
- [x] `_resolve_sandbox_name` — special chars sanitized
- [x] `_should_cleanup` — default truthy
- [x] `_should_cleanup` — env var set to "0"
- [x] `_should_cleanup` — env var set to "false"
- [x] `_should_cleanup` — env var set to "1"
- [x] `_execution_mode` — returns "docker-sandbox"
- [x] `_wrap_sandbox_exec` — builds correct docker command
- [x] `_wrap_sandbox_exec` — forwards env vars
- [x] `_wrap_sandbox_exec` — skips unset env vars
- [x] `_build_failure_message` — auth failure (not logged in)
- [x] `_build_failure_message` — auth failure (authentication_failed)
- [x] `_build_failure_message` — non-auth delegates to claude base
- [x] `_build_failure_message` — appends sandbox note when missing
- [x] `_build_failure_message` — no duplicate sandbox note
- [x] `_command_not_found_message` — returns sandbox-specific message
- [x] `_fallback_command_when_not_found` — returns None
- [x] `_docker_sandbox_available` — success (returncode 0)
- [x] `_docker_sandbox_available` — failure (returncode != 0)
- [x] `_docker_sandbox_available` — FileNotFoundError
- [x] `_ensure_sandbox` — skips when already created
- [x] `_ensure_sandbox` — docker not on PATH raises RuntimeError
- [x] `_ensure_sandbox` — sandbox not available raises RuntimeError
- [x] `_ensure_sandbox` — success (full creation path with mocked subprocess)
- [x] `_ensure_sandbox` — create failure raises RuntimeError
- [x] `_ensure_sandbox` — with template env var
- [x] `_ensure_sandbox` — verbose mode emits command
- [x] `_remove_sandbox` — skips when not created
- [x] `_remove_sandbox` — removes when created (stop + rm subprocess)

### Phase 2: meta/skills edge case tests (94% -> 98%)

- [x] `normalize_skill_selection` — None returns empty
- [x] `normalize_skill_selection` — non-string in list raises ValueError
- [x] `_discover_catalog` — no catalog dir returns empty dict
- [x] `_discover_catalog` — extracts title from heading
- [x] `stage_skill_catalog` — nonexistent source skipped
- [x] `validate_skill_names` — accepts valid names

### Phase 3: Validation

- [x] All tests pass (1225 passed, 6 skipped)
- [x] Lint and format clean
- [x] Update `docs/QUALITY_SCORE.md` with new coverage notes
- [x] Update `docs/PLANS.md`
- [x] Move plan to completed

---

## Completion criteria

- All Phase 1-3 tasks checked off
- `uv run pytest -v` passes
- `uv run ruff check . && uv run ruff format --check .` passes
