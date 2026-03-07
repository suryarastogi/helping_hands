# Usage Monitoring

How helping_hands tracks Claude Code API consumption via automated usage
logging.

## Context

Teams using Claude Code through the OAuth flow need visibility into their
API consumption to avoid hitting rate limits unexpectedly. Rather than
manual checks, the system automates usage polling and persists historical
snapshots for trend analysis.

## Decision

Usage monitoring is implemented as a Celery task (`log_claude_usage`) in
`server/celery_app.py` with three independent stages: token retrieval,
API call, and database persistence. Each stage fails independently so
partial results are still surfaced.

### Architecture

```
macOS Keychain                Anthropic OAuth API           Postgres
(credentials)                 (usage endpoint)              (claude_usage_log)
     |                              |                            |
     v                              v                            v
 security find-generic-password  GET /api/oauth/usage        INSERT usage row
     |                              |                            |
     +------> log_claude_usage <----+----------------------------+
                    |
                    v
              Task result dict
              {status, session_pct, weekly_pct}
```

### Token retrieval

OAuth credentials are read from the macOS Keychain via
`security find-generic-password -s "Claude Code-credentials" -w`. The raw
output is parsed in two ways:

1. **JSON credential blob** -- `{"claudeAiOauth": {"accessToken": "..."}}`
2. **Raw JWT fallback** -- if JSON parsing fails and the value starts with
   `ey`, it is treated as a bare JWT token.

If neither produces a valid token, the task returns early with an error dict.

### Usage API

The task calls `https://api.anthropic.com/api/oauth/usage` with the OAuth
bearer token. The response contains two usage windows:

- **`five_hour`** -- session utilization percentage and reset timestamp
- **`seven_day`** -- rolling weekly utilization and reset timestamp

HTTP errors and general exceptions are caught separately to provide
specific error messages.

### Database persistence

Usage snapshots are written to a `claude_usage_log` table in Postgres. The
table is auto-created via DDL on first write (`CREATE TABLE IF NOT EXISTS`).
Each row records:

- `session_pct` / `session_resets_at` (five-hour window)
- `weekly_pct` / `weekly_resets_at` (seven-day window)
- `raw_response` (full JSON for debugging)

The `DATABASE_URL` is resolved from the environment with a hardcoded
development default.

### Scheduling

`ensure_usage_schedule()` registers an hourly RedBeat entry (idempotent;
safe to call on every worker startup via `on_after_finalize`). If RedBeat
or Redis is unavailable, the registration silently no-ops.

### Independent failure stages

Each stage returns an error dict independently:

| Stage | Failure | Behavior |
|---|---|---|
| Keychain | `security` command fails or token missing | Returns `{status: "error", message: ...}` |
| API | HTTP error or network failure | Returns `{status: "error", message: ...}` |
| DB write | `psycopg2` unavailable or connection error | Returns error dict **with** `session_pct`/`weekly_pct` (data still surfaced) |
| Success | All stages pass | Returns `{status: "ok", session_pct, weekly_pct}` |

## Alternatives considered

1. **Claude Code CLI `--usage` flag** -- Rejected; requires spawning a
   subprocess and parsing CLI output. Direct API calls are simpler and
   more reliable.
2. **In-memory metrics only** -- Rejected; historical trend data requires
   persistence. In-memory counters are lost on worker restart.
3. **Separate monitoring service** -- Rejected as over-engineering; a single
   Celery task with RedBeat scheduling is sufficient for hourly polling.

## Consequences

- Usage data is available for dashboards and alerting via SQL queries
  against `claude_usage_log`.
- The three-stage independent failure model means a Keychain issue never
  prevents the task from reporting, and a DB outage still surfaces
  utilization percentages in the task result.
- macOS-specific (`security` command) -- this monitoring path only works
  on macOS hosts with the Claude Code OAuth credentials in Keychain.
- Tests cover all error paths via mocked subprocess/urllib/psycopg2 calls.

## Source references

- `src/helping_hands/server/celery_app.py` -- `log_claude_usage()`,
  `ensure_usage_schedule()`, `_get_db_url_writer()`, `_USAGE_TABLE_DDL`,
  `_USAGE_INSERT`
