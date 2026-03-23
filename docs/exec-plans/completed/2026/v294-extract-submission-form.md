# v294: Extract SubmissionForm Component

**Status:** Completed
**Date:** 2026-03-23

## Goal

Extract the inline `submissionCard` JSX block (~152 lines) from `App.tsx` into a
dedicated `SubmissionForm` component, continuing the frontend decomposition effort.

## Tasks

- [x] Create `SubmissionForm.tsx` with typed props extracted from App.tsx inline block
- [x] Create `SubmissionForm.test.tsx` with 17 component tests
- [x] Replace inline submissionCard JSX in App.tsx with `<SubmissionForm />` component

## Changes

### New files
- `frontend/src/components/SubmissionForm.tsx` — Presentational form component with
  `SubmissionFormProps` interface (form state, onFieldChange callback, onSubmit handler).
  Renders repo path input, prompt input, Run button, and Advanced settings panel
  (backend select, model, max iterations, PR number, tools, skills, checkboxes for
  no-PR/execution/web/native-auth/fix-CI, GitHub token, reference repos).
- `frontend/src/components/SubmissionForm.test.tsx` — 17 tests covering rendering,
  input callbacks, checkbox toggles, backend select, form submission, password field,
  and reference repos.

### Modified files
- `frontend/src/App.tsx` — Replaced 152-line inline `submissionCard` JSX with single
  `<SubmissionForm>` component invocation. Added import. App.tsx reduced from 2,043
  to 1,891 lines (-152 lines).

## Test results

- **Frontend:** 378 tests passing (up from 361, +17 new)
- **Backend:** 6,311 tests passing (no changes)
- **Lint/typecheck/format:** All green
