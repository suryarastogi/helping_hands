# v327 — Sync Task Status with GitHub Issue

**Date:** 2026-03-28
**Intent:** Deeper GitHub integration — sync task status with GitHub issue

## Problem

When a task has a linked `issue_number` (either manually provided or auto-created
via `create_issue`), the issue is updated with a PR link comment during PR
finalization. But there is no lifecycle tracking — the issue doesn't reflect
whether the task is in progress, completed successfully, or failed. Users must
check the helping-hands UI to see task status.

## Solution

Add issue lifecycle labels and status comments so GitHub issues reflect task
progress in real-time:

1. **`GitHubClient.add_issue_labels()`** — add labels to an issue
2. **`GitHubClient.remove_issue_label()`** — remove a single label (best-effort)
3. **`_sync_issue_started()`** in `celery_app.py` — adds `helping-hands:in-progress` label when task begins
4. **`_sync_issue_completed()`** — posts summary comment with PR link + runtime, swaps label to `helping-hands:completed`, removes `in-progress`
5. **`_sync_issue_failed()`** — posts failure comment, swaps label to `helping-hands:failed`, removes `in-progress`
6. **`issue_number` in progress metadata** — include in `_update_progress()` so frontend can display it
7. **Frontend issue badge** — show linked issue number in MonitorCard header when present

## Implementation Steps

- [x] Add `GitHubClient.add_issue_labels()` and `remove_issue_label()` methods
- [x] Add `_sync_issue_started()`, `_sync_issue_completed()`, `_sync_issue_failed()` helpers
- [x] Wire helpers into `build_feature` task lifecycle
- [x] Include `issue_number` in progress metadata
- [x] Add frontend issue number badge to MonitorCard
- [x] Add backend tests (GitHubClient labels + celery sync helpers)
- [x] Add frontend tests (MonitorCard issue badge)
- [x] Update INTENT.md and docs

## Files Modified

- `src/helping_hands/lib/github.py` — `add_issue_labels()`, `remove_issue_label()`
- `src/helping_hands/server/celery_app.py` — sync helpers, `build_feature` wiring, progress metadata
- `frontend/src/components/MonitorCard.tsx` — issue badge
- `frontend/src/types.ts` — `MonitorCardProps` update
- `tests/test_github.py` — label method tests
- `tests/test_celery_app.py` — sync helper tests
- `frontend/src/components/MonitorCard.test.tsx` — badge tests
