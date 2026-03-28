# v329 — GitHub Projects Board Integration

**Created:** 2026-03-28
**Status:** Completed

## Goal

When a task has a linked GitHub issue (via `issue_number` or `create_issue`),
optionally add the issue to a GitHub Projects v2 board. This completes the
"Project Management" checkbox feature from INTENT.md.

## Context

v325–v328 added issue linking, issue creation, and status sync. The remaining
INTENT.md item under "Deeper GitHub integration" is GitHub Projects board
integration. This plan adds a `project_url` field through the full stack so
users can specify a GitHub Project (v2) to automatically add linked issues to.

## Tasks

- [x] Move v328 to completed
- [x] Add `GitHubClient.add_to_project_v2()` — GraphQL mutation `addProjectV2ItemById`
- [x] Add `project_url` to `build_feature` Celery task parameters
- [x] Add `project_url` to `BuildRequest` and form handler in `app.py`
- [x] Add `_try_add_to_project()` helper in `celery_app.py`
- [x] Add `project_url` to frontend `FormState`, `SubmissionForm`, `useTaskManager`
- [x] Add backend tests (GitHubClient method + Celery helper)
- [x] Add frontend tests (SubmissionForm + useTaskManager)
- [x] Update INTENT.md, PLANS.md, Week-13, daily consolidation

## Completion criteria

- User can specify a GitHub Project URL in the UI or API
- After issue creation/linking, the issue is added to the specified project
- Errors are best-effort (never block the build)
- Tests cover success, error, and noop paths

## Results

### `src/helping_hands/lib/github.py`

- Added `_graphql()` private method — executes GitHub GraphQL API calls via `urllib.request`
- Added `_PROJECT_URL_RE` regex — matches org and user project URLs
- Added `parse_project_url()` static method — extracts owner type, owner, and project number from URL
- Added `add_to_project_v2()` method — resolves project/content node IDs via GraphQL, then calls `addProjectV2ItemById` mutation
- Supports both direct `content_id` and `full_name` + `issue_number` resolution

### `src/helping_hands/server/celery_app.py`

- Added `project_url: str | None = None` parameter to `build_feature` task
- Added `_try_add_to_project()` helper — best-effort wrapper that calls `add_to_project_v2()` and swallows errors
- Called after issue creation/linking, before hand execution

### `src/helping_hands/server/app.py`

- Added `project_url: str | None = None` to `BuildRequest` model
- Added `project_url: str | None = Form(None)` to form handler
- Threaded `project_url` through `_enqueue_build()` to Celery task

### Frontend

- `FormState.project_url: string` added to types
- `INITIAL_FORM.project_url = ""` default
- `SubmissionForm`: Project URL text input with placeholder
- `useTaskManager`: sends `project_url` in submit body when non-empty, URL query param support

### Tests

- 11 new backend tests: 6 `TestParseProjectUrl` + 5 `TestAddToProjectV2` (GitHubClient), 4 `TestTryAddToProject` (Celery helper), 5 `TestBuildForm` updated with `project_url` field
- 4 new frontend tests: 2 `SubmissionForm` (render + change), 2 `useTaskManager` (include + omit)
- 7516 backend tests passed (up from 7501), 0 failures
- 98.17% coverage
