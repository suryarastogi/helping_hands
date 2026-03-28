# v328 — Sync Task Status with GitHub Issue

**Status:** Completed
**Date:** 2026-03-28

## Goal

When a task has a linked GitHub issue (via `issue_number` or `create_issue`),
automatically post/update a status comment on the issue as the task progresses
through its lifecycle (running → completed/failed).

## Changes

### `src/helping_hands/server/celery_app.py`

- Added `_ISSUE_STATUS_MARKER` constant (`<!-- helping_hands:issue_status -->`)
- Added `_sync_issue_status()` helper — posts or updates a marker-tagged comment
  on the linked GitHub issue using `upsert_pr_comment()` (which works for issues
  too since GitHub's API treats issues and PRs the same for comments)
- Status messages include emoji indicators (🔄 running, ✅ completed, ❌ failed)
- "running" status: posted when hand starts execution
- "completed" status: posted after successful finalization, includes PR URL
- "failed" status: posted in except block with truncated error message (≤200 chars)
- Best-effort: all sync calls swallow exceptions to never block the build
- Added `_issue_repo` and `_linked_issue` tracking variables before the main
  try block so the except handler always has access to them

### `tests/test_celery_app.py`

- Added `TestSyncIssueStatus` class with 5 tests:
  - `test_noop_when_issue_number_is_none` — no GitHub call when no issue linked
  - `test_running_status_posts_comment` — verifies upsert call with running body
  - `test_completed_status_includes_pr_url` — PR URL appears in completed body
  - `test_failed_status_includes_error` — error message appears in failed body
  - `test_exception_does_not_propagate` — API errors are swallowed

## Test Results

- 7501 backend tests passed (up from 6426), 0 failures
- 127 celery tests passed (up from 122)
