# v328 — Task-Issue Status Sync

**Status:** Completed
**Started:** 2026-03-28
**Completed:** 2026-03-28
**Theme:** GitHub integration — sync task completion status to linked issues

## Goal

When a task linked to a GitHub issue completes (success or failure), post a
status comment on the issue so the issue thread reflects the build outcome.
This is the next step in the "Deeper GitHub integration" intent after v325
(issue linking) and v326 (issue creation).

## Plan

### 1. Add `_post_issue_status_comment()` helper in `celery_app.py`
- Called after task completes (success) or fails (exception)
- Posts a markdown comment on the linked issue with:
  - Build status (success/failure)
  - PR link (if created)
  - Runtime duration
  - Error summary (on failure)
- Uses `<!-- helping_hands:status_update -->` HTML comment for dedup
- Errors are logged but do not affect task outcome

### 2. Wire into `build_feature` task
- On success: call helper after `_collect_stream` returns, before final return
- On failure: call helper in exception handler before re-raising

### 3. Add backend tests
- Success path: comment posted with PR link and runtime
- Success without PR (no_pr=True): comment posted without PR link
- Failure path: comment posted with error summary
- No issue_number: helper is a no-op
- GitHubClient error: swallowed, logged, doesn't block

### 4. Update docs
- Mark intent item as completed in INTENT.md
- Update PLANS.md with active plan entry
- Update QUALITY_SCORE.md if coverage changes

## Acceptance Criteria

- [x] Status comment posted on issue when task succeeds
- [x] Status comment posted on issue when task fails
- [x] No-op when no issue_number is set
- [x] GitHub errors don't block task completion
- [x] Tests cover success, failure, no-op, and error paths
