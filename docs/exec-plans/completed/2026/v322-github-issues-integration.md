# v322 — GitHub Issues Integration (Project Management)

**Created:** 2026-03-27
**Status:** Completed
**Theme:** First phase of deeper GitHub integration — the "Project Management" checkbox

## Goal

Add a `project_management` boolean flag to the task submission flow. When enabled:
1. A GitHub issue is created from the task prompt before execution begins
2. The resulting PR body includes `Closes #N` to auto-link and close the issue on merge

## Tasks

- [x] Add `IssueResult` dataclass and `create_issue()`/`get_issue()` to GitHubClient
- [x] Add `project_management` flag to BuildRequest, ScheduleRequest, ScheduleResponse, ScheduledTask
- [x] Wire `project_management` through `_enqueue_build_task()` and `build_feature()` celery task
- [x] Add `issue_number` to Hand base class; prepend `Closes #N` in `_create_new_pr()`
- [x] Add "Project Mgmt" checkbox to SubmissionForm and ScheduleCard
- [x] Add `project_management` to FormState, ScheduleFormState, ScheduleItem, useSchedules
- [x] Wire `project_management` in useTaskManager submit body
- [x] Add 19 backend tests + 3 frontend tests
- [x] Update INTENT.md, PLANS.md, design doc

## Completion criteria

- All existing tests pass with the new field added
- New backend tests cover IssueResult, create_issue, get_issue, Hand.issue_number, PR body linking
- Frontend typecheck and lint pass
- SubmissionForm renders and toggles the "Project Mgmt" checkbox

## Changes

### Backend — `lib/github.py`
- Add `IssueResult` dataclass (number, url, title)
- Add `create_issue()` method to `GitHubClient`
- Add `get_issue()` method to `GitHubClient`
- Update `__all__` exports

### Backend — `server/app.py`
- Add `project_management: bool = False` to `BuildRequest`
- Wire through `_enqueue_build_task()`

### Backend — `server/celery_app.py`
- Accept `project_management` parameter in `build_feature()`
- When enabled + GitHub token available: create issue, pass issue number to hand
- Include issue metadata in result dict

### Backend — `lib/hands/v1/hand/base.py`
- Add `issue_number` property to Hand
- When `issue_number` is set and a PR is created, prepend `Closes #N` to PR body

### Frontend — `types.ts`
- Add `project_management: boolean` to `FormState`

### Frontend — `SubmissionForm.tsx`
- Add "Project Mgmt" checkbox in the check-grid

### Frontend — `useTaskManager.ts`
- Include `project_management` in submit body

### Tests
- Backend: GitHubClient.create_issue, get_issue
- Backend: build_feature with project_management flag
- Frontend: SubmissionForm checkbox rendering and toggle
- Frontend: useTaskManager submit body inclusion

## Out of Scope (future phases)
- Linking to *existing* GitHub issues (requires issue search UI)
- GitHub Projects board integration
- Issue label/milestone management
- Sync task status with issue comments
