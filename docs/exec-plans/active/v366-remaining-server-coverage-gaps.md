# v366 — Remaining Server Coverage Gaps

**Created:** 2026-04-05
**Status:** Active
**Theme:** Close last coverage gaps in server modules to push toward 99%+ with extras

## Context

With server extras installed, overall coverage is 98.71% (86 lines missing).
The biggest gaps are:

| Module | Lines missing | What |
|---|---|---|
| `server/app.py` | 52 | Grill enabled-path endpoints (POST/GET), lifespan |
| `server/schedules.py` | 24 | `_launch_interval_chain`, `_get_redis_client`, import fallbacks |
| `server/multiplayer_yjs.py` | 4 | pycrdt fallback import |
| `cli/main.py` | 3 | Edge cases (already 98%) |
| `server/grill.py` | 2 | Branch hints (already 98%) |

## Tasks

- [x] Test grill enabled-path endpoints (~30 lines)
  - `POST /grill` — mock `grill_session.delay`, assert response shape
  - `POST /grill/{id}/message` — mock Redis, test session-exists and push
  - `GET /grill/{id}` — mock Redis, test not_found + message drain
- [x] Test `_launch_interval_chain` (~48 lines)
  - Mock `build_feature.apply_async` and `interval_reschedule.si`
  - Verify chain construction, nonce persistence, meta save
  - Test ImportError fallback path
- [x] Test `_get_redis_client` (4 lines)
  - Mock `redis.from_url` with Celery app conf
- [x] Test app lifespan (3 lines)
  - Mock `start_yjs_server`/`stop_yjs_server`, exercise async context
- [x] Update docs (INTENT.md, QUALITY_SCORE.md, Week-14)

## Completion criteria

- Coverage with server extras: 98.71% → 99%+
- All existing tests still pass
- No mocking of external services beyond what's necessary
