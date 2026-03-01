# PRD: Type Safety, Error Handling, Provider Tests & Doc Reconciliation

**Date:** 2026-03-01
**Status:** Completed
**Scope:** Code quality hardening and cross-surface documentation alignment

---

## Goals

1. Eliminate no-op and redundant exception handling patterns across hand implementations
2. Replace loose `Any` type annotations with concrete types in core hand classes
3. Add unit test coverage for AI provider modules (currently untested)
4. Validate `enabled_skills` entries against known skill names at config time
5. Reconcile minor drift between documentation surfaces (README, AGENT.md, Obsidian, MkDocs)

## Non-Goals

- Frontend refactoring (App.tsx split) — separate PRD
- CI type-checker step — deferred per TODO.md until `ty` GA release
- Security scanning tooling — separate concern

## Success Criteria

- [x] Zero no-op `except Exception: raise` patterns in src/
- [x] Hand constructors use `Config` and `RepoIndex` types instead of `Any`
- [x] AI provider test file expanded from 10 to 28 tests (≥5 per provider area)
- [x] `Config.__post_init__` warns on unrecognized skill names
- [x] Obsidian Project Log W09 updated with this session's outcomes
- [x] All changes pass `ruff check`, `ruff format --check`, and `pytest` (510 tests passing)

---

## TODO

- [x] **T1 — Error handling cleanup**: Removed no-op `except Exception: raise` in `atomic.py:93-94` and `iterative.py:902-903` (BasicAtomicHand.stream)
- [x] **T2 — Type annotation tightening**: Replaced `config: Any, repo_index: Any` with `Config`/`RepoIndex` (TYPE_CHECKING) in `_BasicIterativeHand`, `BasicLangGraphHand`, `BasicAtomicHand`, `AtomicHand`, and `_TwoPhaseCLIHand`
- [x] **T3 — AI provider unit tests**: Expanded `tests/test_ai_providers.py` from 10→28 tests: provider attributes, `_build_inner` ImportError→RuntimeError, lazy init, model override, `acomplete`, `normalize_messages` edge cases
- [x] **T4 — Config skills validation**: Added `_validate_skills()` in `config.py` + 4 tests in `test_config.py` (valid/empty/unknown/multiple-unknown)
- [x] **T5 — Doc reconciliation**: Updated Obsidian W09 log, AGENT.md recurring decisions (+3 entries), AGENT.md last-updated timestamp

---

## Activity Log

1. PRD created after full codebase audit (13 completed PRDs reviewed, 4 doc surfaces audited, code gaps analyzed)
2. T1: Removed 2 no-op `except Exception: raise` patterns from `atomic.py` and `iterative.py`
3. T2: Added `TYPE_CHECKING` imports and replaced `Any` with `Config`/`RepoIndex` in 5 hand constructors; removed unused `Any` import from `cli/base.py`
4. T3: Added 18 new tests to `test_ai_providers.py` (provider attributes, ImportError handling, lazy init, model override, acomplete, normalize edge cases)
5. T4: Added `_validate_skills()` function and wired into `Config.__post_init__`; added 4 tests
6. Lint/format/test verification: all 510 tests passing, ruff clean
7. T5: Updated Obsidian W09 log, AGENT.md recurring decisions and timestamp
8. PRD marked complete; moved to `completed/` with datetime and semantic title
