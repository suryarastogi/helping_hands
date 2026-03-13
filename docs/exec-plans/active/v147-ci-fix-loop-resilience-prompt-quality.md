## v147 — CI fix loop resilience and prompt quality improvements

**Status:** Active
**Created:** 2026-03-13

## Goal

Three self-contained improvements to the CI fix loop in `cli/base.py`:

1. **`_poll_ci_checks` API exception resilience** — `gh.get_check_runs()` calls at lines 826 and 836 have no exception handling. A transient GitHub API failure (network error, rate limit, 5xx) crashes the entire poll loop. Add try-except with warning logging and retry within the poll loop, and a safe fallback for the final post-deadline call.

2. **`_build_ci_fix_prompt` URL formatting cleanup** — When `html_url` is empty, the prompt line `- name: conclusion ()` has empty parentheses. Omit parentheses entirely when URL is empty for cleaner AI context.

3. **`_ci_fix_loop` exception debug logging** — The broad `except Exception` at line 1006 logs the message string via `emit()` but doesn't log the stack trace. Add `logger.debug` with `exc_info=True` for diagnosability, consistent with the project convention of always logging before suppressing exceptions (v129 pattern).

## Tasks

- [x] Add try-except in `_poll_ci_checks` poll loop to catch exceptions from `gh.get_check_runs()` with warning log and continue
- [x] Add try-except for the final `gh.get_check_runs()` call after deadline with safe fallback dict
- [x] Fix URL formatting in `_build_ci_fix_prompt` to omit parentheses when `html_url` is empty
- [x] Add `logger.debug` with `exc_info=True` in `_ci_fix_loop` exception handler
- [x] Add tests for `_poll_ci_checks` API exception scenarios (5 tests: transient retry, warning log, all-fail fallback, post-deadline fallback, post-deadline warning log)
- [x] Add tests for `_build_ci_fix_prompt` URL formatting (4 tests: present URL, empty URL, missing URL key, mixed URLs)
- [x] Add tests for `_ci_fix_loop` exception debug logging (2 tests: debug log with exc_info, exception type in message)
- [x] Run lint and tests — 3553 passing, 80 skipped
- [x] Update docs (PLANS.md, QUALITY_SCORE.md, Week-11)

## Completion criteria

- All new tests pass (11 new tests)
- `ruff check` and `ruff format` pass
- Docs updated with v147 notes
