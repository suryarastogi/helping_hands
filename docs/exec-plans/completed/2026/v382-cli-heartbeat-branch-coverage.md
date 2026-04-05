# v382 — CLI Heartbeat-Without-Timeout Branch Coverage

**Created:** 2026-04-05
**Status:** Completed

## Goal

Cover the `1284->1293` branch partial in `cli/base.py` where the heartbeat
interval has NOT elapsed during a TimeoutError, so the heartbeat message is
skipped and the IO loop continues. This is the last actionable branch gap in
the CLI hand IO loop.

## Context

The IO loop in `_invoke_cli_with_cmd` has a heartbeat check (line 1284) and
an idle timeout check (line 1293). Existing tests cover the case where BOTH
fire (idle timeout test). The missing branch is when the heartbeat fires but
idle timeout hasn't been reached — the loop should `continue` and eventually
the process finishes normally.

Also resolves the tech debt tracker item "CLI IO loop heartbeat-without-timeout
branch" from `Low` to `Resolved`.

## Tasks

- [x] Create active plan v382
- [x] Add `test_no_heartbeat_when_interval_not_elapsed` to `test_cli_hand_base_invoke.py`
- [x] Verify the branch `1284->1293` is now covered (BrPart 15→14)
- [x] Update tech debt tracker (moved to resolved)
- [x] Update docs (PLANS.md, INTENT.md, Week-14)

## Completion criteria

- New test covers heartbeat emission without triggering idle timeout
- Branch `1284->1293` covered
- Tech debt item resolved
- All tests pass
- Docs updated

## Files changed

- `tests/test_cli_hand_base_invoke.py`
- `docs/exec-plans/tech-debt-tracker.md`
- `docs/exec-plans/active/v382-cli-heartbeat-branch-coverage.md`
- `docs/PLANS.md`
- `INTENT.md`
- `docs/exec-plans/completed/2026/Week-14.md`
