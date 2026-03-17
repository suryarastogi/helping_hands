# v248 — Extract git-not-found constants, narrow run_async exception handling

**Status:** Completed
**Date:** 2026-03-17

## Problem

`pr_description.py` used 4 bare "git not found on PATH" debug messages (2 variants)
and 2 bare "CLI not found" debug messages. These should be module-level constants
for consistency with the existing constant pattern in the file.

`atomic.py:158` and `iterative.py:1289` both had `except Exception:` blocks that
only log and re-raise. These were narrowed to `except (RuntimeError, TypeError,
ValueError, AttributeError, OSError):` since `run_async` is an internal library
method; `AssertionError` is already handled separately.

## Tasks

- [x] Create this plan
- [x] Add `_GIT_NOT_FOUND_DIFF_MSG` and `_GIT_NOT_FOUND_UNCOMMITTED_MSG` constants to `pr_description.py`
- [x] Add `_CLI_NOT_FOUND_MSG` constant to `pr_description.py`
- [x] Replace 4 bare "git not found" strings with constants
- [x] Replace 2 bare "CLI not found" strings with constant
- [x] Narrow `except Exception` in `atomic.py:158` to specific types
- [x] Narrow `except Exception` in `iterative.py:1289` to specific types
- [x] Add AST-based test: no bare "git not found" strings remain in pr_description.py
- [x] Add behavioral tests for exception narrowing
- [x] Run full test suite + lint

## Completion criteria

- Zero bare "git not found on PATH" strings in `pr_description.py`
- Zero bare "CLI not found" strings in `pr_description.py`
- No `except Exception` in `atomic.py` or `iterative.py` run_async handlers
- All new tests pass
- Full test suite passes with no regressions
- Lint and format checks clean

## Changes

### `src/helping_hands/lib/hands/v1/hand/pr_description.py`
- Added 3 constants: `_GIT_NOT_FOUND_DIFF_MSG`, `_GIT_NOT_FOUND_UNCOMMITTED_MSG`,
  `_CLI_NOT_FOUND_MSG`
- Replaced 4 bare "git not found on PATH" strings with constants
- Replaced 2 bare "%s CLI not found ..." strings with constant-based expressions

### `src/helping_hands/lib/hands/v1/hand/atomic.py`
- Narrowed `except Exception:` at line 158 to
  `except (RuntimeError, TypeError, ValueError, AttributeError, OSError):`

### `src/helping_hands/lib/hands/v1/hand/iterative.py`
- Narrowed `except Exception:` at line 1289 to
  `except (RuntimeError, TypeError, ValueError, AttributeError, OSError):`

### `tests/test_v248_git_not_found_constants_narrow_exceptions.py` (new)
- 22 tests across 4 test classes
- Constant values, types, distinctness, non-empty
- AST-based source checks for pr_description.py (no bare strings remain)
- AST-based source checks for atomic.py and iterative.py (no `except Exception`)
- Behavioral tests for constant usage and formatting

## Test results

- **22 new tests** (0 skipped)
- **5877 passed**, 249 skipped, 0 failures
- All lint/format checks pass
- 78.44% coverage
