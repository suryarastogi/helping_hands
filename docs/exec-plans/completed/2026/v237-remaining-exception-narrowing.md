# v237 — Narrow remaining `except Exception` in hand base, CLI base, and server app

**Created:** 2026-03-16
**Status:** Completed

## Goal

Narrow 5 remaining `except Exception` handlers to specific exception types,
continuing the pattern established in v230–v236:

1. **base.py:936** — `gh.update_pr_body()` → `(GithubException, OSError)`
2. **base.py:1232** — `_finalize_repo_pr` catch-all → `(GithubException, OSError)`
3. **cli/base.py:1544** — `_ci_fix_loop` → `(GithubException, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError)`
4. **app.py:3705** — `_resolve_worker_capacity` → `(KeyError, TypeError, ValueError, OSError)`
5. **app.py:3842** — `_schedule_to_response` next_run → `(ValueError, TypeError)`

## Tasks

- [x] Create this plan
- [x] Narrow `except Exception` in base.py (2 sites)
- [x] Narrow `except Exception` in cli/base.py (1 site)
- [x] Narrow `except Exception` in app.py (2 sites)
- [x] Add tests (24 new: all passed)
- [x] Run lint, format, type check, pytest
- [x] Update docs

## Completion criteria

- All 5 handlers narrowed to specific exception types
- All changes have tests
- Lint, format, type check pass
- Full test suite passes with no regressions

## Files changed

- `src/helping_hands/lib/hands/v1/hand/base.py` — Narrow 2 `except Exception` → `except (GithubException, OSError)`
- `src/helping_hands/lib/hands/v1/hand/cli/base.py` — Import `GithubException`, narrow 1 `except Exception` → `except (GithubException, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError)`
- `src/helping_hands/server/app.py` — Narrow 2 `except Exception` → specific types
- `tests/test_v237_remaining_exception_narrowing.py` — 24 new AST + runtime tests
- `tests/test_v115_code_quality.py` — Update mock side_effect from `RuntimeError` → `GithubException`
- `tests/test_v188_redact_dry_debug_logging.py` — Update mock side_effects from `TypeError` → `GithubException`/`OSError`
- `tests/test_cli_hand_base_ci_loop.py` — Update mock side_effect from `RuntimeError` → `OSError`
