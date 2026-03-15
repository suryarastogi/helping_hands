# v203 — DRY auth failure detection + text truncation helper

**Date:** 2026-03-15

## Changes

**DRY `_detect_auth_failure` helper:** Extracted `_detect_auth_failure(output, extra_tokens=())` function in `cli/base.py` that encapsulates the repeated 3-line pattern (tail extraction via `_FAILURE_OUTPUT_TAIL_LENGTH`, lowercase conversion, `_AUTH_ERROR_TOKENS` + extra tokens check) previously duplicated across 4 CLI hand subclasses. Returns `(is_auth_failure, tail)` tuple. Refactored `claude.py`, `codex.py`, `gemini.py`, and `opencode.py` to use the new helper, removing direct imports of `_AUTH_ERROR_TOKENS` and `_FAILURE_OUTPUT_TAIL_LENGTH` from all 4 subclasses.

**DRY `_truncate_with_ellipsis` helper:** Extracted `_truncate_with_ellipsis(text, limit)` function in `cli/base.py` replacing 4× inline `text[:limit - 3] + "..."` patterns in `claude.py`'s `_StreamJsonEmitter` (text preview, tool result preview, Bash command, CronCreate prompt truncation).

**Updated 3 existing test files** (`test_v139_constants.py`, `test_v166_dry_truthy_docstrings.py`, `test_v193_dry_auth_tokens_docstrings.py`) to reflect that subclasses now use `_detect_auth_failure` instead of directly importing `_AUTH_ERROR_TOKENS`/`_FAILURE_OUTPUT_TAIL_LENGTH`.

## Tests

50 new tests in `test_v203_dry_auth_detection_truncation.py`:
- 8 `_truncate_with_ellipsis` unit tests (boundary, ellipsis, no-op)
- 11 `_detect_auth_failure` unit tests (tokens, extras, case, tail length, empty)
- 16 subclass refactoring verification (4× no manual tail, imports helper, no direct constant imports)
- 5 `_StreamJsonEmitter` truncation verification (no inline slicing, functional)
- 2 `__all__` export tests
- 8 functional failure message tests (auth + generic for each backend)

4873 passed, 196 skipped.
