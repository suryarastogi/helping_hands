# PRD: CLI Hand Robustness, Docstring Gaps & Cross-Surface Doc Reconciliation

**Status:** Completed
**Created:** 2026-03-01
**Completed:** 2026-03-01
**Goal:** Harden CLI hand internals (exception specificity, recursive retry safety, missing docstrings on private helpers), expand test coverage for untested code paths (stream, interrupt, subprocess env), and reconcile documentation across all surfaces (README, AGENT.md, Obsidian, MkDocs, docstrings).

---

## Problem Statement

1. **Bare `except Exception` in `claude.py:100`** — `_skip_permissions_enabled()` catches all exceptions when checking `geteuid()`, masking potential bugs. Should catch specific exception types.
2. **Recursive retry without depth guard in `base.py:538`** — `_invoke_cli_with_cmd` calls itself recursively for fallback/retry with no depth limit. Currently safe (max 1 level) but fragile for future backends.
3. **13+ private methods across CLI hands lack docstrings** — `_truncate_summary`, `_is_truthy`, `_float_env`, `_looks_like_edit_request`, `_terminate_active_process`, `_collect_run_output`, `_invoke_claude`, `_invoke_codex`, `_invoke_gemini`, `_has_goose_builtin_flag`, `_normalize_goose_provider`, `_infer_goose_provider_from_model`, `_normalize_ollama_host`.
4. **No tests for `stream()` method** — the async streaming path in `_TwoPhaseCLIHand` has zero test coverage.
5. **No tests for `interrupt()` / `_terminate_active_process()`** — cooperative interruption flow is untested.
6. **Obsidian test count stale** — Project todos.md says 569 tests; actual count may differ after recent additions.
7. **AGENT.md and Obsidian Project Log W10 need session entry** for this work.

---

## Success Criteria

- [x] `except Exception` in `claude.py` replaced with specific exception types
- [x] Recursive retry in `base.py` guarded with max depth
- [x] All 13+ private methods have Google-style docstrings (20+ total added)
- [x] `test_cli_hands.py` gains tests for `stream()` happy path
- [x] `test_cli_hands.py` gains tests for `interrupt()` during run
- [x] Obsidian Project todos.md test count updated (579)
- [x] Obsidian Project Log W10 updated with session entry
- [x] AGENT.md updated with new recurring decisions (3 entries)
- [x] All surfaces consistent (test counts, module counts, feature lists)

---

## Non-Goals

- Adding tests for container execution (Docker) — requires Docker runtime
- Refactoring the two-phase flow architecture
- Adding new CLI hand backends
- MkDocs page additions (all 36 pages already exist)

---

## TODO

### P0 — Code quality and safety

- [x] Replace bare `except Exception` in `claude.py:100` with `(ValueError, TypeError, OSError)`
- [x] Add max-depth guard to `_invoke_cli_with_cmd` recursive calls in `base.py` (`_MAX_CLI_RETRY_DEPTH = 2`)
- [x] Add Google-style docstrings to 20+ private methods across CLI hands (base.py, claude.py, codex.py, goose.py, gemini.py)

### P1 — Test coverage expansion

- [x] Add `TestTwoPhaseCLIHandStream` test class for `stream()` happy path (2 tests)
- [x] Add `TestTwoPhaseCLIHandInterrupt` test class for `interrupt()` during run (4 tests)
- [x] Add `TestTwoPhaseCLIHandTerminateProcess` test class (3 tests)
- [x] Add `TestMaxRetryDepth` test class (1 test)

### P2 — Cross-surface documentation reconciliation

- [x] Update Obsidian `Project todos.md` with current test count (579)
- [x] Update Obsidian `Project Log/2026-W10.md` with session entry
- [x] Update `AGENT.md` recurring decisions with 3 new entries
- [x] Update Obsidian `AGENT.md` summary with new recurring decisions and test counts
- [x] Verify README, CLAUDE.md, Obsidian Architecture/Concepts consistency

---

## Activity Log

| Date | Action |
|------|--------|
| 2026-03-01 | PRD created after full codebase audit (CLI hands, docs, tests, Obsidian) |
| 2026-03-01 | P0 executed: replaced bare `except Exception` with `(ValueError, TypeError, OSError)` in claude.py |
| 2026-03-01 | P0 executed: added `_MAX_CLI_RETRY_DEPTH` guard to recursive retry in base.py |
| 2026-03-01 | P0 executed: added Google-style docstrings to 20+ private methods across 5 CLI hand files |
| 2026-03-01 | P1 executed: added 10 tests (stream, interrupt, terminate, retry depth) — 579 total tests passing |
| 2026-03-01 | P2 executed: reconciled AGENT.md, Obsidian AGENT.md, Project todos.md, Project Log W10 |
| 2026-03-01 | All lint checks passing, all 579 tests passing, PRD completed |
