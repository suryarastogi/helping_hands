# v317 — useRecentRepos Hook Test Coverage

**Date:** 2026-03-27
**Status:** Completed
**Theme:** Frontend test coverage — close the last untested hook gap

## Context

All custom hooks in `frontend/src/hooks/` have co-located test files except
`useRecentRepos`. This hook manages a localStorage-backed "recently used repos"
list with dedup, ordering, cap, cross-tab sync, and add/remove operations.

## Tasks

1. Create `frontend/src/hooks/useRecentRepos.test.tsx` with tests covering:
   - Initial state loads from localStorage
   - `addRepo` moves a repo to front, deduplicates, caps at 20
   - `addRepo` with empty/whitespace string is a no-op
   - `removeRepo` removes the specified repo
   - Cross-tab sync via `storage` event
   - localStorage errors (quota exceeded) are handled gracefully
2. Update FRONTEND.md hook listing with useRecentRepos test file
3. Update INTENT.md with completion entry
4. Consolidate plan to completed/

## Success criteria

- All new tests pass
- No regressions in existing 596 tests
- useRecentRepos has >80% statement and branch coverage
