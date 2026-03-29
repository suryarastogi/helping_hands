# v319 — App.tsx & useTaskManager Branch Coverage

**Goal:** Raise branch coverage for `App.tsx` (69% → 80%+) and `useTaskManager.ts`
(72% → 80%+) with semantically meaningful tests.

**Date:** 2026-03-27
**Status:** Completed

## Tasks

- [x] Write tests for `App.tsx` `fetchServerConfig()` effect branches
- [x] Write tests for `useTaskManager.ts` uncovered branches
- [x] Verify branch coverage improvements meet 80%+ target

## Results

### App.tsx: 69.23% → 81.25% branch coverage
4 new tests covering `fetchServerConfig()` effect branches:
- Server config applies `native_auth_default` and filters `enabled_backends`
- Backend replaced when current backend not in filtered enabled list
- Claude usage panel hidden when `claude_native_cli_auth === false`
- Server config fetch skipped when `use_native_cli_auth` URL param is explicit

### useTaskManager.ts: 72.03% → 82.68% branch coverage
13 new tests covering:
- `fetchedCapacity` set after polling resolves
- `submitRun` includes optional body fields (`github_token`, `reference_repos`,
  `model`, `pr_number`, `tools`, `skills`)
- `submitRun` skips `pr_number` when not a valid number
- Primary polling updates status and stops on terminal status
- Primary polling handles poll error gracefully
- Query-string initialization: `task_id`+`status`, `error` param, form field params
- `outputTab` raw and payload modes
- Current tasks discovery merges discovered tasks
- `runtimeDisplay` returns null when no task running
- `taskInputs` derives input items from payload

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| App.tsx branch | 69.23% | 81.25% |
| useTaskManager.ts branch | 72.03% | 82.68% |
| Overall branch | 88.55% | 90.23% |
| Frontend tests | 657 | 674 |
