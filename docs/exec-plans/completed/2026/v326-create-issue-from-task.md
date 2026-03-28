# v326 — Create New Issue from Task

**Date:** 2026-03-28
**Status:** complete
**Branch:** helping-hands/claudecodecli-9f34267c
**Goal:** Allow users to create a new GitHub issue from a task, with the task prompt as the issue body. The created issue is then automatically linked to the PR.

## Context

INTENT.md requests: "When creating a task, option to create a new issue from the task
(with task prompt as issue body)". v325 added linking to existing issues via
`issue_number`. This plan adds the ability to *create* a new issue automatically.

## Tasks

- [x] Add `GitHubClient.create_issue()` method (title, body, labels)
- [x] Add `create_issue` boolean to `BuildRequest` in `app.py`
- [x] Add `create_issue` parameter to `build_feature` Celery task
- [x] In `build_feature`, when `create_issue=True` and `issue_number` is None,
      create a new issue using the prompt, then set `hand.issue_number`
- [x] Add `create_issue` to frontend `FormState`, `INITIAL_FORM`, `SubmissionForm`
- [x] Add `create_issue` to `useTaskManager` submit body
- [x] Backend tests: GitHubClient.create_issue(), Celery auto-create logic
- [x] Frontend tests: SubmissionForm checkbox, useTaskManager submit
- [x] Update INTENT.md, PLANS.md, daily/weekly consolidation

## Completion criteria

- `create_issue` checkbox in frontend Advanced settings ✓
- When enabled: new GitHub issue created with task prompt as body ✓
- Created issue number flows into existing `issue_number` pipeline ✓
- PR gets "Closes #N" and issue gets PR link comment ✓
- Tests cover new code paths ✓
- Docs updated ✓

## Results

- **Backend tests:** 5 new GitHubClient tests + 4 Celery helper tests = 9 new
- **Frontend tests:** 724 → 728 (+4: 2 SubmissionForm, 2 useTaskManager)
- **Files changed:** `github.py`, `app.py`, `celery_app.py`, `types.ts`,
  `App.utils.ts`, `SubmissionForm.tsx`, `useTaskManager.ts` + 4 test files
