# PRD: MkDocs Hand Documentation Expansion & Cross-Surface Reconciliation

**Status:** Completed
**Created:** 2026-03-01
**Completed:** 2026-03-01
**Goal:** Expand MkDocs API documentation to cover all Hand implementation modules individually (currently only the package-level `__init__.py` is documented), add missing docstrings to CLI hand base public methods, and reconcile cross-surface documentation (Obsidian, TODO.md, Project Log).

---

## Problem Statement

The Hand abstraction is the core of helping_hands, yet the MkDocs API documentation only has a single page (`api/lib/hands/v1/hand.md`) pointing at the package `__init__.py`. The 13 individual implementation modules — including the Hand base class, iterative engine, LangGraph/Atomic backends, E2E workflow, four CLI backends, model provider, and PR description generator — are invisible in the published docs site. This makes the API reference incomplete for the project's most important subsystem.

Additionally, several public methods in `cli/base.py` (`_TwoPhaseCLIHand`) lack Google-style docstrings, which means mkdocstrings will generate empty stubs for them.

## Success Criteria

- [x] All Hand implementation modules have dedicated MkDocs API doc pages
- [x] `mkdocs.yml` nav includes all new hand doc pages
- [x] `docs/index.md` references the expanded hand documentation
- [x] Public/semi-public methods in `cli/base.py` have Google-style docstrings
- [x] Obsidian Project Log W09 updated with this session's work
- [x] Obsidian `Project todos.md` updated with hand doc expansion milestone
- [x] AGENT.md updated with recurring decisions for hand docs and CLI base docstrings
- [x] All documentation surfaces are consistent
- [x] All 488 tests pass, lint/format clean

## Non-Goals

- Rewriting existing docstrings that are already adequate
- Adding docstrings to obvious private one-liner helpers (e.g. `_is_truthy`)
- Changing code behavior or adding features
- Adding a docstring linter to CI

---

## TODO

### 1. Create MkDocs API doc pages for Hand implementations
- [x] `docs/api/lib/hands/v1/hand/base.md` — Hand base class, HandResponse
- [x] `docs/api/lib/hands/v1/hand/iterative.md` — _BasicIterativeHand engine
- [x] `docs/api/lib/hands/v1/hand/langgraph.md` — LangGraphHand
- [x] `docs/api/lib/hands/v1/hand/atomic.md` — BasicAtomicHand
- [x] `docs/api/lib/hands/v1/hand/e2e.md` — E2EHand
- [x] `docs/api/lib/hands/v1/hand/model_provider.md` — Model resolution
- [x] `docs/api/lib/hands/v1/hand/pr_description.md` — PR description generation
- [x] `docs/api/lib/hands/v1/hand/cli/base.md` — _TwoPhaseCLIHand
- [x] `docs/api/lib/hands/v1/hand/cli/claude.md` — ClaudeCodeHand
- [x] `docs/api/lib/hands/v1/hand/cli/codex.md` — CodexCLIHand
- [x] `docs/api/lib/hands/v1/hand/cli/goose.md` — GooseCLIHand
- [x] `docs/api/lib/hands/v1/hand/cli/gemini.md` — GeminiCLIHand

### 2. Update mkdocs.yml navigation
- [x] Add all 12 new hand doc pages under `hands` nav section
- [x] Organize into core modules and `cli` subsection

### 3. Update docs/index.md
- [x] Add expanded hand documentation references to the API overview

### 4. Add docstrings to CLI hand base public methods (~25 methods)
- [x] `_normalize_base_command()` — command token normalization
- [x] `_base_command()` — resolve CLI command from env
- [x] `_resolve_cli_model()` — model string resolution
- [x] `_apply_backend_defaults()` — backend-specific flag injection
- [x] `_container_enabled()` — container mode check
- [x] `_container_image()` — container image resolution
- [x] `_container_env_names()` — env vars to forward into container
- [x] `_use_native_cli_auth()` — native CLI auth check
- [x] `_native_cli_auth_env_names()` — auth env var names
- [x] `_effective_container_env_names()` — combined env names
- [x] `_wrap_container_if_enabled()` — Docker wrapping logic
- [x] `_execution_mode()` — host vs container mode label
- [x] `_build_subprocess_env()` — subprocess environment construction
- [x] `_build_failure_message()` — error message formatting
- [x] `_command_not_found_message()` — missing CLI error
- [x] `_fallback_command_when_not_found()` — fallback command resolution
- [x] `_retry_command_after_failure()` — recoverable failure retry
- [x] `_build_init_prompt()` — phase-1 init prompt
- [x] `_build_task_prompt()` — phase-2 task prompt
- [x] `_repo_has_changes()` — git diff detection
- [x] `_invoke_cli()` — CLI invocation
- [x] `_invoke_cli_with_cmd()` — subprocess lifecycle management
- [x] `_interrupted_pr_metadata()` — interruption metadata
- [x] `_finalize_after_run()` — PR finalization dispatch
- [x] `_format_pr_status_message()` — PR status formatting
- [x] `interrupt()` — cooperative interruption (override docstring)
- [x] `run()` — synchronous execution (override docstring)
- [x] `stream()` — async streaming execution (override docstring)

### 5. Reconcile cross-surface documentation
- [x] Update AGENT.md with recurring decisions for hand docs and CLI base docstrings
- [x] Update Obsidian `Project todos.md` with hand doc expansion design note
- [x] Update Obsidian Project Log W09 with this session's contribution

---

## Activity Log

| Date | Action |
|------|--------|
| 2026-03-01 | PRD created; identified 12 missing MkDocs hand doc pages and ~19 undocumented CLI hand base methods |
| 2026-03-01 | Created 12 MkDocs API doc pages for all Hand implementation modules (core + CLI); updated mkdocs.yml nav with organized subsections |
| 2026-03-01 | Updated docs/index.md with 12 new hand documentation links |
| 2026-03-01 | Added ~25 Google-style docstrings to _TwoPhaseCLIHand methods in cli/base.py |
| 2026-03-01 | Updated AGENT.md with 2 new recurring decisions (hand docs, CLI base docstrings); updated last-updated timestamp |
| 2026-03-01 | Updated Obsidian Project Log W09 and Project todos with hand doc expansion milestone |
| 2026-03-01 | All 488 tests passing, lint/format clean. PRD completed; moving to completed/ |
