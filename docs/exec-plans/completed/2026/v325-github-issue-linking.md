# v325 — GitHub Issue Linking

**Date:** 2026-03-28
**Intent:** Deeper GitHub integration — link tasks to GitHub issues

## Context

INTENT.md requests GitHub Issues and Projects integration. The most
self-contained first step: when a user provides a GitHub issue number with
their task, the system should:

1. Include "Closes #N" in the generated PR body so GitHub auto-closes the
   issue when the PR merges
2. Post a comment on the issue linking to the created PR
3. Accept issue_number through the full stack (frontend → API → Celery → Hand)

## Plan

- [x] Add `get_issue()` and `create_issue_comment()` to `GitHubClient`
- [x] Add `issue_number` field to `BuildRequest` in server `app.py`
- [x] Add `issue_number` parameter to `build_feature` Celery task
- [x] Add `issue_number` attribute to `Hand` base class
- [x] Wire issue linking into `_create_new_pr` and `_push_to_existing_pr`:
  - Append "Closes #N" to PR body
  - Post issue comment with PR link after PR creation/update
- [x] Add `issue_number` to frontend `FormState`, `INITIAL_FORM`, and `SubmissionForm`
- [x] Add `issue_number` to `useTaskManager` submit body
- [x] Backend tests: GitHubClient issue methods, Hand issue linking
- [x] Frontend tests: SubmissionForm issue field, useTaskManager issue submit
- [x] Update INTENT.md, PLANS.md, docs

## Outcome

Users can optionally provide a GitHub issue number when submitting a task.
The created/updated PR will reference the issue with "Closes #N" and a
comment is posted on the issue linking to the PR.
