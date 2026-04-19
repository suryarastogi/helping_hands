# INTENT.md

User intents and desires for the helping-hands project.

## Active Intents

_No active intents._

## Waiting On

### Configure GHA Runner Orphan Process Kill Setting (2026-04-19)

On lugiawyvern (`192.168.10.13`), add `ACTIONS_RUNNER_KILL_ORPHANED_PROCESSES=false`
to the GHA self-hosted runner's `.env` file (likely `~/actions-runner/.env`), then
restart the runner service. This prevents GHA's post-job cleanup from killing the
background services (server, worker, frontend) that `run-local-stack.sh` starts.
Current workaround: `RUNNER_TRACKING_ID=""` in the deploy workflow step env block.
