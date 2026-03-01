# PRD: CLI Hand Test Coverage & Documentation Reconciliation

**Created:** 2026-03-01
**Completed:** 2026-03-01
**Status:** Completed

**Goal:** Close the largest remaining test coverage gap (CLI hand implementations) and reconcile documentation across all surfaces (README, AGENT.md, Obsidian, MkDocs, docstrings).

## Problem

The codebase has strong test coverage (449+ tests) across core library modules, but the four CLI hand implementations (`claude.py`, `codex.py`, `goose.py`, `gemini.py`) plus the `placeholders.py` backward-compat shim and `default_prompts.py` have **zero dedicated unit tests**. These modules contain significant business logic (auth detection, fallback commands, retry strategies, model resolution, provider injection) that should be validated.

Additionally, documentation across README, AGENT.md, Obsidian vault, and MkDocs API docs has minor drift that should be reconciled.

## Success Criteria

- [x] CLI hand implementations have unit tests covering key business logic
- [x] `placeholders.py` has basic import/re-export tests
- [x] `default_prompts.py` has basic content tests
- [x] Documentation surfaces are reconciled (timestamps, cross-references, content alignment)
- [x] All tests pass (`uv run pytest -v`) — 471 passed
- [x] Linting passes (`uv run ruff check .`)

## TODO

### P0 — Test Coverage (Critical)

- [x] **CLI hand tests**: Created `tests/test_cli_hands.py` with 86+ unit tests:
  - `ClaudeCodeHand`: model filtering (GPT dropped), skip-permissions logic, root detection, fallback to npx, retry without --dangerously-skip-permissions, failure message parsing, permission prompt detection, native auth env names
  - `CodexCLIHand`: default model (gpt-5.2), sandbox mode auto-detection (host vs container), skip-git-repo-check injection, normalize base command, failure message parsing, native auth env names
  - `GooseCLIHand`: provider/model resolution from config, ollama host normalization, GitHub token requirement, env injection, builtin developer flag injection, normalize base command, provider normalization, provider inference, CLI model resolution
  - `GeminiCLIHand`: approval-mode injection, model-not-found detection, strip-model-args retry, API key requirement, failure message parsing
  - `_TwoPhaseCLIHand` (shared base): truncate_summary, is_truthy, looks_like_edit_request, float_env, build_init_prompt, build_task_prompt, build_apply_changes_prompt
- [x] **Placeholders tests**: Created `tests/test_placeholders.py` — 4 tests verifying re-exports, __all__ contents, backward-compat stdlib symbols, identity with canonical imports
- [x] **Default prompts tests**: Created `tests/test_default_prompts.py` — 7 tests verifying prompt constant is non-empty, contains expected markers (@@READ, @@FILE, @@TOOL, README.md)

### P1 — Documentation Reconciliation

- [x] **AGENT.md**: Updated dependency table — clarified `redis` as transitive via `celery[redis]`, noted `croniter` is in pyproject.toml under server extra. Added CLI hand test coverage recurring decision entry. Updated last-updated timestamp.
- [x] **Obsidian Project Log**: Added W09 entry for CLI hand test coverage & doc reconciliation work.
- [x] **Obsidian Project todos**: Added design notes for CLI hand test coverage milestone and AGENT.md dependency clarification.

## Non-Goals

- Adding integration tests that require live CLI installations
- Refactoring CLI hand implementations
- Adding new features or capabilities

## Activity Log

- **2026-03-01 (Hand):** PRD created. Identified 6 untested modules, prioritized CLI hands as highest-impact gap.
- **2026-03-01 (Hand):** Created `tests/test_cli_hands.py` with 86+ unit tests covering all four CLI hand implementations plus shared base class helpers. Created `tests/test_placeholders.py` (4 tests) and `tests/test_default_prompts.py` (7 tests). All tests passing.
- **2026-03-01 (Hand):** Fixed lint issues (unused import, combined `with` statements per SIM117). All checks pass.
- **2026-03-01 (Hand):** Documentation reconciliation: updated AGENT.md dependency table (redis transitive, croniter location), added recurring decision for CLI hand test coverage, updated Obsidian Project Log W09, updated Obsidian Project todos design notes. Full test suite: 471 passed, 3 skipped.
- **2026-03-01 (Hand):** PRD completed. Moving to `completed/` directory.
