# v246 — Simplify defensive getattr(self.config, ...) to direct attribute access

**Status:** Completed
**Date:** 2026-03-16

## Problem

All hand files used `getattr(self.config, "field", default)` to read `Config`
attributes defensively. Since `Config` is a frozen dataclass where every field
has a default value, the `getattr` fallback was unnecessary. Direct attribute
access (`self.config.field`) is cleaner, type-safe, and avoids hiding typos.

12 occurrences across 4 files:
- `base.py` (7): `enabled_tools`, `enable_execution` ×2, `enable_web`,
  `enabled_skills`, `use_native_cli_auth`, `github_token`
- `iterative.py` (2): `enable_execution`, `enable_web`
- `cli/base.py` (2): `use_native_cli_auth`, `github_token`
- `e2e.py` (1): `github_token`

## Tasks

- [x] Create this plan
- [x] Replace 7 `getattr` calls in `base.py` with direct access
- [x] Replace 2 `getattr` calls in `iterative.py` with direct access
- [x] Replace 2 `getattr` calls in `cli/base.py` with direct access
- [x] Replace 1 `getattr` call in `e2e.py` with direct access
- [x] Add AST-based test ensuring no `getattr(self.config, ...)` remains
- [x] Add behavioral tests for config attribute access
- [x] Run full test suite + lint

## Completion criteria

- Zero `getattr(self.config, ...)` calls remain in hand source files
- AST-based regression test prevents reintroduction
- All 21 new tests pass
- Full test suite passes with no regressions
- Lint and format checks clean

## Changes

### `src/helping_hands/lib/hands/v1/hand/base.py`
- Replaced 7 `getattr(self.config, ...)` with direct `self.config.field` access
- `enabled_tools`, `enable_execution`, `enable_web`, `enabled_skills`,
  `use_native_cli_auth`, `github_token`

### `src/helping_hands/lib/hands/v1/hand/iterative.py`
- Replaced 2 `getattr(self.config, ...)` in `_execution_tools_enabled()` and
  `_web_tools_enabled()`

### `src/helping_hands/lib/hands/v1/hand/cli/base.py`
- Replaced 2 `getattr(self.config, ...)` in `_use_native_cli_auth()` and
  `_ci_fix_loop()`

### `src/helping_hands/lib/hands/v1/hand/e2e.py`
- Replaced 1 `getattr(self.config, ...)` in `run()` GitHubClient instantiation

### `tests/test_v246_config_direct_access.py` (new)
- 21 passed
- AST source consistency: no `getattr(self.config, ...)` in 4 hand files
- Config dataclass field guarantee tests (defaults, frozen, field coverage)
- Behavioral tests across Hand, _BasicIterativeHand, _TwoPhaseCLIHand

## Test results

- **21 new tests** (0 skipped)
- **5826 passed**, 249 skipped, 0 failures
- All lint/format checks pass
