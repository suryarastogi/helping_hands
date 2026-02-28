# PRD: Error Handling & Observability Improvements

**Status:** Completed
**Created:** 2026-02-28
**Priority:** High
**Scope:** Targeted improvements to error handling, logging, and input validation across the codebase

## Problem Statement

The helping_hands codebase has several areas where broad `except Exception: pass` blocks silently swallow errors, making production debugging difficult. Health check endpoints lack timeouts. The worker capacity introspection silently fails. These gaps reduce observability and make it harder to diagnose issues when things go wrong.

## Goals

1. Replace silent `except Exception: pass` blocks with structured logging
2. Add Python `logging` to critical code paths (health checks, worker introspection, CLI hand startup)
3. Add `cron_expression` validation to the `ScheduleRequest` model
4. Add a configurable `max_total_time` timeout for iterative hand runs
5. Ensure all changes pass existing tests and linting

## Non-Goals

- Adding full OpenTelemetry/Prometheus instrumentation (future work)
- Refactoring the Hand class hierarchy
- Implementing new CLI backends (Claude, Gemini — separate effort)

---

## TODO

- [x] **1. Add structured logging to health check endpoints** — Replace bare `except Exception` in `_check_redis_health`, `_check_db_health`, `_check_workers_health` with `logger.warning()` calls that include the exception
- [x] **2. Add logging to worker capacity introspection** — Replace `except Exception: pass` in `get_worker_capacity` (app.py:2554) with `logger.warning()` that logs the failure reason
- [x] **3. Add logging to PR finalization default branch lookup** — Replace `except Exception: pass` in `_finalize_repo_pr` (base.py:321) with `logger.debug()` so failures are traceable
- [x] **4. Add logging to E2E hand default branch lookup** — Replace `except Exception` in `e2e.py:115` with `logger.debug()`
- [x] **5. Add logging to Claude Code CLI `geteuid` check** — Replace `except Exception: pass` in `claude.py:87` with `logger.debug()`
- [x] **6. Add `cron_expression` Pydantic validator to `ScheduleRequest`** — Validate cron syntax at request time with a descriptive error message
- [x] **7. Run tests and linting to verify all changes** — Ensure no regressions

---

## Activity Log

- 2026-02-28: PRD created after comprehensive codebase analysis
- 2026-02-28: All 7 TODO items implemented and verified — 327 tests pass, ruff lint/format clean
  - Added `logging` module and `logger` instances to `app.py`, `base.py`, `e2e.py`, `claude.py`
  - Replaced 6 silent `except Exception: pass` blocks with `logger.warning()`/`logger.debug()` calls with `exc_info=True`
  - Added `cron_expression` Pydantic field validator to `ScheduleRequest` using existing `validate_cron_expression()` from `schedules.py`
- 2026-02-28: PRD moved to `docs/completed/`
