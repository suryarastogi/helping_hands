# v347 — Server Route Coverage & API Endpoint Tests

**Date**: 2026-04-01
**Status:** Completed
**Goal**: Add HTTP-level tests for untested server API routes

## Context

The server module (`app.py`) has extensive tests for helper functions and the
`/build/form` endpoint but several key HTTP routes used by the frontend lack
direct route-level tests:

- `POST /build` (JSON API — the main programmatic endpoint)
- `GET /tasks/{task_id}` (task status lookup)
- `POST /tasks/{task_id}/cancel` (task cancellation)
- `GET /config` (runtime configuration)
- `GET /notif-sw.js` (service worker script)
- `GET /health/multiplayer` family (4 endpoints)

## Changes

### New file: `tests/test_server_app_routes.py` (20 tests)

- **TestBuildJsonEndpoint** (7 tests) — valid JSON build request, default backend,
  empty repo/prompt validation, invalid backend rejection, optional fields
  passthrough, max_iterations upper bound validation
- **TestGetTaskEndpoint** (3 tests) — pending, completed, and failed task states
- **TestCancelTaskEndpoint** (2 tests) — cancel running task, refuse terminal task
- **TestConfigEndpoint** (3 tests) — Docker/non-Docker config, GitHub token
  detection, Claude native auth flag
- **TestNotifServiceWorker** (1 test) — JavaScript content type and body
- **TestMultiplayerHealthEndpoints** (4 tests) — stats, players, activity,
  decorations endpoints

### Updated file: `tests/test_server_app_coverage.py` (6 tests)

- **TestResolveTaskWorkspace** (6 tests) — workspace from metadata, repo_path
  fallback, repo key fallback, no workspace error, completed cleanup error,
  running not-found error

## Tasks

- [x] Add route-level tests for `POST /build` JSON API
- [x] Add route-level tests for `GET /tasks/{task_id}` and `POST /tasks/{task_id}/cancel`
- [x] Add route-level tests for `GET /config` and `GET /notif-sw.js`
- [x] Add route-level tests for multiplayer health endpoints
- [x] Add `resolve_task_workspace` unit tests

## Results

- 26 new tests added
- 287 server tests passed, 0 failures
- No regressions in existing test suite
- Coverage improvement on `app.py` routes
