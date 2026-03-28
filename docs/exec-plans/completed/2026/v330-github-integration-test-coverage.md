# v330 — GitHub Integration Test Coverage

**Status:** completed
**Created:** 2026-03-28
**Theme:** Fill integration test gaps for v325–v329 GitHub features

## Motivation

The v325–v329 series added full-stack GitHub issue linking, issue creation,
status sync, and Projects v2 board integration. Unit tests cover the helper
functions and API methods well, but **integration-level gaps** exist at the
server form endpoint, hand PR body generation, and Celery helper edge cases:

1. `enqueue_build_form` never tested with non-default issue/project values
2. PR body "Closes #N" generation untested in hand base `_create_new_pr`
3. Invalid project URL edge case not covered in `_try_add_to_project`

## Tasks

- [x] Add `TestBuildForm` tests submitting `issue_number`, `create_issue`, `project_url`
- [x] Add test verifying PR body contains "Closes #N" when `issue_number` set
- [x] Add test verifying PR body omits "Closes #" when `issue_number` is None
- [x] Add invalid `project_url` edge case test for `_try_add_to_project`
- [x] Update PLANS.md and INTENT.md

## Completion criteria

All new tests pass. No regressions in existing test suite. PLANS.md updated
with v330 entry. Active plan moved to completed when done.

## Results

- 2 new `TestBuildForm` tests (issue_number, create_issue + project_url)
- 2 new `TestCreateNewPrIssueClose` tests (PR body with/without issue_number)
- 1 new `TestTryAddToProject` test (invalid project URL swallowed)
- 5 new tests total, 6438 tests passed, 0 failures
