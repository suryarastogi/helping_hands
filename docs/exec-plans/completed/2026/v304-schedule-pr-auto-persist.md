# v304 — Schedule PR Auto-Persist

**Status:** Completed
**Date:** 2026-03-26
**Theme:** Auto-persist newly created PR numbers back to scheduled tasks

## Goal

When a scheduled task creates a new PR (i.e. `pr_number` is empty on the
schedule), automatically persist the created PR number back to the schedule.
Subsequent runs then push to the same PR instead of creating new ones.

This addresses the user intent: "if pr number is empty on a scheduled task it
should create the PR the first time and on subsequent runs it should update the
same PR."

## Tasks

- [x] Add `last_pr_metadata` attribute to `Hand` base class — stores
      finalization metadata after `_finalize_repo_pr()` completes.
- [x] Add `update_pr_number()` method to `ScheduleManager` — focused
      write of just the `pr_number` field to an existing schedule.
- [x] Add `_maybe_persist_pr_to_schedule()` helper in `celery_app.py` —
      bridges hand result to schedule storage with guard conditions.
- [x] Add `schedule_id` parameter to `build_feature` Celery task —
      optional, passed from `scheduled_build` and `trigger_now`.
- [x] Wire auto-persist into both E2E and non-E2E hand paths in
      `build_feature`, and spread `hand.last_pr_metadata` into the
      non-E2E result dict.
- [x] Add 18 new tests (4 ScheduleManager, 7 celery helper, 7 hand
      instantiation).
- [x] Lint + format pass.

## Result

- Scheduled builds now auto-persist PR numbers: first run creates PR,
  subsequent runs update the same PR.
- Guard conditions prevent writes when: no schedule context, PR already
  set, hand didn't create a PR, or result is non-numeric.
- Errors during persist are logged but never block the build result.
- 18 new tests across 3 test files.
