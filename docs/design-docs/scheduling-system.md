# Scheduling System

How helping_hands implements cron-based recurring task scheduling using RedBeat
and Redis.

## Context

The server mode supports recurring builds (e.g. "run this prompt against the
repo every weekday at 9 AM").  Rather than building a custom scheduler, the
system leverages RedBeat -- a celery-redbeat extension that stores cron entries
in Redis and triggers them through Celery's beat process.

## Architecture

```
Frontend / API                  Redis                     Celery Beat
┌───────────────┐        ┌───────────────────┐        ┌──────────────┐
│ POST /schedule │──────>│ schedule:meta:{id} │        │   RedBeat    │
│ PUT /schedule  │       │   (JSON blob)      │        │   entries    │
│ DELETE /schedule│      │                    │        │   (crontab)  │
└───────────────┘        └───────────────────┘        └──────┬───────┘
                                                              │
                                                              ▼
                                                       ┌──────────────┐
                                                       │ Celery worker │
                                                       │ build_feature │
                                                       └──────────────┘
```

### Dual storage model

Each schedule has two representations in Redis:

1. **Metadata key** (`helping_hands:schedule:meta:{id}`) -- a JSON blob
   containing the full `ScheduledTask` dataclass: cron expression, repo path,
   prompt, backend config, run history, and enabled/disabled state.

2. **RedBeat entry** (`redbeat:helping_hands:scheduled:{id}`) -- a Celery
   crontab entry that triggers `helping_hands.scheduled_build` with the schedule
   ID as its sole argument.

`ScheduleManager` CRUD methods keep these two representations in sync:
creating/deleting both together, and updating by deleting-then-recreating the
RedBeat entry.

## Key design decisions

### Dataclass-driven, no ORM

`ScheduledTask` is a plain `@dataclass` with `to_dict()` / `from_dict()` for
JSON serialization.  No database schema or migration tooling required -- Redis
is the single source of truth.

### Lazy dependency checks

`redbeat` and `croniter` are optional imports guarded by `_check_redbeat()` /
`_check_croniter()`.  The server starts and handles non-schedule requests even
when these packages are absent; only schedule endpoints require the extras.

### Cron presets

Common patterns are mapped in `CRON_PRESETS`:

| Preset | Expression |
|---|---|
| `daily` / `midnight` | `0 0 * * *` |
| `hourly` | `0 * * * *` |
| `weekdays` | `0 9 * * 1-5` |
| `every_5_minutes` | `*/5 * * * *` |

Users can pass either a preset name or a raw five-field cron string.
`validate_cron_expression()` resolves presets and validates via `croniter`.

### Trigger-now

`trigger_now()` dispatches an immediate Celery `build_feature.delay()` using
the schedule's saved parameters, bypassing the cron trigger.  The run is
recorded in metadata (`last_run_at`, `last_run_task_id`, `run_count`).

### Enable/disable without deletion

`enable_schedule()` and `disable_schedule()` toggle the `enabled` flag and
create or delete the RedBeat entry accordingly, without touching the metadata.
This preserves run history across enable/disable cycles.

## CRUD operations

| Operation | Metadata | RedBeat entry |
|---|---|---|
| `create_schedule` | Write | Create (if enabled) |
| `update_schedule` | Write | Delete + recreate (if enabled) |
| `delete_schedule` | Delete | Delete |
| `enable_schedule` | Update `enabled=True` | Create |
| `disable_schedule` | Update `enabled=False` | Delete |
| `record_run` | Update run stats | No change |
| `trigger_now` | Update via `record_run` | No change (immediate dispatch) |

## Alternatives considered

- **Database-backed schedules** -- rejected; adds migration complexity and a
  Postgres dependency for a feature that only needs key-value storage.
- **APScheduler** -- mature but heavier; RedBeat integrates natively with
  Celery's beat process, avoiding a second scheduler daemon.
- **OS-level cron** -- not portable across container deployments; no API for
  dynamic CRUD.

## Consequences

- Schedule state lives entirely in Redis.  Losing Redis loses all schedule
  definitions (acceptable for the current deployment model; backup strategies
  can be added later).
- The `ScheduleManager` constructor validates RedBeat availability eagerly, so
  schedule-related API endpoints fail fast rather than at trigger time.
- Run metadata (count, last run) is eventually consistent -- a crash between
  task dispatch and `record_run` could miss a count increment.
