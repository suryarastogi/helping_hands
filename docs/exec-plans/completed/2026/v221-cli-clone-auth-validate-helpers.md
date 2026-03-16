# v221 — DRY git clone helper, auth status line, and validation wrapper

**Date:** 2026-03-16
**Status:** Completed

## Goal

Extract three sets of duplicated patterns into shared helpers:

1. Git clone subprocess logic duplicated between `_resolve_repo_path()` and `_clone_reference_repos()` in `cli/main.py`
2. Auth status banner logic duplicated between `BasicLangGraphHand.stream()` and `BasicAtomicHand.stream()` in `iterative.py`
3. Validation-or-exit pattern repeated 3× in `main()` in `cli/main.py`

## Changes

### `src/helping_hands/cli/main.py`

- **`_run_git_clone(url, dest, *, label)`**: New helper encapsulating `subprocess.run` with `--depth`, timeout handling, non-zero exit handling, and stderr redaction. Used by both `_resolve_repo_path()` and `_clone_reference_repos()`.
- **`_validate_or_exit(fn, *args, **kwargs)`**: New helper wrapping a callable in try/except ValueError → stderr + sys.exit(1). Replaces 3 identical try-except blocks in `main()`.
- **`_REPO_SPEC_PATTERN`**: New module-level constant for the `owner/repo` regex, replacing inline regex in `_resolve_repo_path()`.

### `src/helping_hands/lib/hands/v1/hand/iterative.py`

- **`_auth_status_line()`**: New instance method on `_BasicIterativeHand` returning the `[backend] provider=... | auth=... (set/not set)` banner. Replaces 6-line inline blocks in both `BasicLangGraphHand.stream()` and `BasicAtomicHand.stream()`.

### Tests

- **`tests/test_v221_cli_clone_auth_validate.py`**: 37 tests across 5 classes:
  - `TestRunGitClone` (7): success, timeout, nonzero exit, empty stderr fallback, label in error, callable check, docstring
  - `TestValidateOrExit` (7): success return, exit on error, args passthrough, kwargs passthrough, stderr output, callable check, docstring
  - `TestRepoSpecPattern` (9): 4 valid specs, 5 invalid specs
  - `TestAuthStatusLine` (8): env var present/absent/whitespace, backend name, provider name, newline termination, method check, docstring
  - `TestSourceConsistency` (6): stream methods use `_auth_status_line`, `_resolve_repo_path`/`_clone_reference_repos` use `_run_git_clone`, `main()` uses `_validate_or_exit`, `_resolve_repo_path` uses `_REPO_SPEC_PATTERN`
- **`tests/test_v172_reference_repo_coverage.py`**: 2 existing tests updated for new error message format (assertions now check individual keywords instead of exact message string)

## Results

- **37 new tests, 2 existing tests updated**
- **5331 passed, 219 skipped**, coverage 78.68%
