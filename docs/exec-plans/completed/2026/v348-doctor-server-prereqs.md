# v348 — Doctor Server-Mode Prerequisite Checks

**Status:** completed
**Created:** 2026-04-04

## Goal

Extend `helping-hands doctor` with checks for server-mode prerequisites:
Redis CLI (`redis-cli`) and Docker Compose (`docker compose`). These are
required when running the full server stack via `docker compose up` or
`./scripts/run-local-stack.sh`. Also fix pre-existing docs index gaps and
missing README sections.

## Tasks

- [x] Add `_check_redis_cli()` to doctor.py — checks `redis-cli` on PATH
      (needed for local-stack server mode)
- [x] Add `_check_docker_compose()` to doctor.py — checks `docker compose`
      subcommand availability (needed for app-mode deployment)
- [x] Wire both checks into `collect_checks()` under the optional tools section
- [x] Add `collect_checks` and `format_results` to `__all__` export
- [x] Fix docs/index.md — add references to app-mode.md, backends.md, development.md
- [x] Fix README.md — add missing Configuration and Development sections
- [x] Write tests for both new checks (8 new tests: 2 redis-cli, 5 docker-compose, 1 collect_checks)
- [x] Run full test suite to verify no regressions (6591 passed, 0 failures)
- [x] Update INTENT.md, PLANS.md, and Week-14 consolidation

## Completion criteria

- `_check_redis_cli()` and `_check_docker_compose()` exist and are wired into `collect_checks()`
- At least 7 new tests covering all branches of both checks
- `docs/index.md` references all top-level docs (app-mode.md, backends.md, development.md)
- README.md has Configuration and Development sections
- All existing tests pass (no regressions)
- PLANS.md, INTENT.md, and Week-14 consolidation updated

## Rationale

Doctor already checks for Docker CLI and Node.js (v347) but doesn't check for
Redis CLI or Docker Compose, both of which are required for server-mode
operation. Users running `docker compose up` or the local stack script encounter
failures without clear guidance — `doctor` should surface these missing
dependencies proactively.
