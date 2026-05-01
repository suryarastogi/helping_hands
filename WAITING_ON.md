# Waiting On

Items blocked on external input, decisions, or dependencies.

## Active blockers

| Item | Blocked on | Since | Notes |
|---|---|---|---|
| GHA runner orphan kill setting | Manual config on lugiawyvern | 2026-04-19 | Add `ACTIONS_RUNNER_KILL_ORPHANED_PROCESSES=false` to `~/actions-runner/.env` on lugiawyvern, then restart the runner service. Prevents GHA post-job cleanup from killing background services started by `run-local-stack.sh`. Workaround in place: `RUNNER_TRACKING_ID=""` in deploy workflow env block. |

## Resolved blockers

| Item | Resolved | Notes |
|---|---|---|
| *(none)* | — | — |

---

*Last updated: 2026-04-19*
