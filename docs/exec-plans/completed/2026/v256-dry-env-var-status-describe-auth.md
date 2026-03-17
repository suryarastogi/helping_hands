# v256: DRY _env_var_status() helper for CLI auth descriptions

**Status:** completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Problem

The `"set" if os.environ.get(env_var, "").strip() else "not set"` pattern is
duplicated across 5 locations in CLI hand `_describe_auth()` methods:

1. `cli/base.py:544` — `os.environ.get(n, "").strip()` in list comprehension
2. `cli/claude.py:316` — `os.environ.get("ANTHROPIC_API_KEY", "").strip()`
3. `cli/gemini.py:48` — `os.environ.get("GEMINI_API_KEY", "").strip()`
4. `cli/goose.py:72` — `os.environ.get(env_var, "").strip()`
5. `cli/opencode.py:59` — `os.environ.get(env_var, "").strip()`

Each duplicates the same "check env var -> return set/not set" logic.

## Tasks

- [x] Add `_env_var_status(name: str) -> str` static method to `_TwoPhaseCLIHand`
  returning `"set"` or `"not set"`
- [x] Replace inline patterns in claude.py, gemini.py, goose.py, opencode.py
- [x] Replace base.py `_describe_auth` list comprehension to use the helper
- [x] Remove local `import os` in gemini.py and goose.py `_describe_auth` where
  it's no longer needed
- [x] Remove stale top-level `import os` in opencode.py (no longer used)
- [x] Add `_env_var_status` tests (set, not set, whitespace-only, empty, missing)
- [x] Add AST source consistency test verifying no inline `os.environ.get` in
  `_describe_auth` methods
- [x] Add stale `import os` regression tests for gemini.py and opencode.py
- [x] Run full test suite: 5988 passed, 270 skipped

## Completion criteria

- All `_describe_auth` methods use `_env_var_status` instead of inline env checks
- No inline `os.environ.get(...).strip()` in `_describe_auth` methods
- All existing tests pass (5988 passed, 270 skipped)
- New tests cover the helper and source consistency (16 tests)
