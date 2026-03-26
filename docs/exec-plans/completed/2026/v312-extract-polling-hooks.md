# v312: Extract useServiceHealth & useClaudeUsage Hooks

**Status:** Active
**Date:** 2026-03-26

## Goal

Continue the App.tsx decomposition by extracting the two remaining polling
effects (service health and Claude usage) into dedicated, testable hooks.
This makes the polling logic independently testable and further reduces
App.tsx complexity.

## Tasks

- [x] Create `useServiceHealth` hook — 15-second polling interval
- [x] Create `useClaudeUsage` hook — 1-hour polling interval + manual refresh
- [x] Update App.tsx to use the new hooks
- [x] Add tests for both hooks
- [x] Run full test suite — confirm all tests pass
- [x] Update docs (FRONTEND.md, PLANS.md, INTENT.md)

## Implementation

### useServiceHealth
- Extracted from App.tsx lines 132–145
- Returns `{ serviceHealthState }`
- 15-second polling interval with cleanup

### useClaudeUsage
- Extracted from App.tsx lines 147–167
- Returns `{ claudeUsage, claudeUsageLoading, refreshClaudeUsage }`
- 1-hour polling interval with manual force-refresh callback
- Server config fetch for native auth default also moved here

## Metrics

- App.tsx: 313 → ~275 lines
- New tests: ~12 (6 per hook)
- Target: all 569+ frontend tests pass
