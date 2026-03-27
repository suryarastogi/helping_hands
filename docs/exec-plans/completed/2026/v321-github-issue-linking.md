# Execution Plan: GitHub Issue Linking

**Created:** 2026-03-27
**Status:** complete
**Branch:** helping-hands/claudecodecli-9f34267c
**Goal:** Add `issue_number` field throughout the full stack so tasks can be linked to GitHub Issues, and created PRs automatically include "Closes #N" in the body.

## Context

The active intent in INTENT.md calls for deeper GitHub integration — specifically, linking tasks to GitHub Issues. This plan implements the most self-contained piece: an `issue_number` field that flows from the frontend form through the API to the Hand, which appends "Closes #N" to PR bodies when set.

## Tasks

- [x] **Backend: Add `issue_number` to data models** — `BuildRequest`, `ScheduleRequest`, `ScheduleResponse` in `app.py`; `ScheduledTask` in `schedules.py`; `build_feature` task in `celery_app.py`; `Hand.issue_number` attribute in `base.py`
- [x] **Backend: Add GitHub client issue methods** — `get_issue()` and `list_issues()` on `GitHubClient` in `github.py`
- [x] **Backend: Wire issue_number into PR body** — Append "Closes #N" in `_generate_pr_title_and_body()` in `base.py` (works with both rich and generic bodies)
- [x] **Backend: Plumb issue_number through enqueue/form** — `_enqueue_build_task()`, `_build_form_redirect_query()`, `enqueue_build_form()` in `app.py`; `trigger_schedule()` in `schedules.py`
- [x] **Frontend: Add `issue_number` to types and forms** — `FormState`, `ScheduleFormState`, `ScheduleItem` in `types.ts`; `INITIAL_FORM`, `INITIAL_SCHEDULE_FORM` in `App.utils.ts`
- [x] **Frontend: Add issue_number input to SubmissionForm and ScheduleCard** — Number input fields in advanced sections
- [x] **Frontend: Wire issue_number in useTaskManager and useSchedules** — Include in request body construction and URL param handling
- [x] **Inline HTML: Add issue_number to both forms** — Main build form and schedule form in `app.py`, including JS payload construction and query param handling
- [x] **Tests: Backend** — GitHubClient.get_issue (3 tests), GitHubClient.list_issues (4 tests), PR body "Closes #N" (3 tests)
- [x] **Tests: Frontend** — SubmissionForm issue_number (3 tests)
- [x] **Documentation** — Updated INTENT.md, PLANS.md, active execution plan

## Completion criteria

- [x] `issue_number` field flows from frontend forms → API → celery task → Hand
- [x] PR bodies include "Closes #N" when issue_number is provided
- [x] GitHubClient has `get_issue()` and `list_issues()` methods
- [x] Backend and frontend tests pass with no regressions
- [x] Both inline HTML and React frontends support the field

## Results

- **Frontend tests:** 681 → 684 (+3)
- **Backend tests:** 10 new (7 GitHub client issue tests, 3 PR body issue linking tests)
- **Files modified:** 11 (app.py, celery_app.py, schedules.py, base.py, github.py, types.ts, App.utils.ts, SubmissionForm.tsx, ScheduleCard.tsx, useTaskManager.ts, useSchedules.ts)
