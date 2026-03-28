# v331 — Server Module Test Coverage Hardening

**Status:** completed
**Created:** 2026-03-28
**Completed:** 2026-03-28
**Goal:** Close remaining testable coverage gaps in `celery_app.py` and `schedules.py` server modules.

## Context

Coverage report shows `celery_app.py` at 5.2% and `schedules.py` at 2.8% overall, but most helper functions already have thorough test suites. The low numbers come from module-level initialization code and `# pragma: no cover` task functions. The remaining *testable* gaps are specific untested branches and classes.

## Completed Tasks

1. **`_ProgressEmitter` direct unit tests** — 4 tests: `emit()` with defaults, with overrides, preserving non-overridden fields, and multiple sequential calls
2. **`_resolve_repo_path` TimeoutExpired branch** — 1 test: mock `subprocess.run` raising `TimeoutExpired`, verify `ValueError` message and temp dir cleanup via `shutil.rmtree`
3. **`_setup_periodic_tasks` signal handler** — 1 test: verify signal handler delegates to `ensure_usage_schedule()`
4. **`_load_meta` corrupted data branch** — 4 tests: invalid JSON returns `None`, logs warning, missing required fields returns `None`, empty required field returns `None`
5. **Consolidate 2026-03-28 plans** — v325–v330 already consolidated in `2026-03-28.md`
6. **Update docs** — INTENT.md, PLANS.md updated

## Tests Added

- 6 new tests in `test_celery_app.py` (`TestProgressEmitter`, `TestResolveRepoPathTimeout`, `TestSetupPeriodicTasks`)
- 4 new tests in `test_schedule_manager.py` (`TestLoadMetaCorruptedData`)
- 10 new tests total, all passing
