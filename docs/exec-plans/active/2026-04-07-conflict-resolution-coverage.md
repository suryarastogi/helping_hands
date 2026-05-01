# 2026-04-07 — Conflict Resolution & Rebase Coverage

Close the largest remaining coverage gaps in `cli/base.py` (88% → 99%) and
`hand/base.py` (92% → 100%) by testing the conflict resolution, rebase, and
push-retry code paths that had zero test coverage.

## Tasks

- [x] Test `_build_conflict_fix_prompt` — pure static method (single file, truncation, empty list)
- [x] Test `_get_conflicted_files` — subprocess mock (success, timeout, OSError)
- [x] Test `_attempt_rebase_with_conflict_fix` — async (fetch fail, no conflicts, conflict resolution success/fail/error, rebase --continue fail)
- [x] Test `_ai_resolve_push_conflicts` — async (not needs_ai, no branch, no conflicts, AI error, remaining conflicts, rebase --continue fail, master rebase, push success/fail)
- [x] Test `_try_rebase_for_push` in `hand/base.py` — (fetch fail, rebase success, conflicts left for AI, non-conflict abort)
- [x] Test `_default_base_branch` success path (git symbolic-ref returns ref)
- [x] Test `_push_to_existing_pr` master_rebase path (rebase ok, rebase fail with abort)
- [x] Test `_push_to_existing_pr` fix_conflicts path (rebase ok + push ok, rebase ok + push fail, rebase fail → needs_ai)
- [x] Verify all tests pass
- [x] Update INTENT.md, PLANS.md, exec-plans index

## Rationale

The conflict resolution code (`_build_conflict_fix_prompt`,
`_get_conflicted_files`, `_attempt_rebase_with_conflict_fix`,
`_ai_resolve_push_conflicts`) and the rebase-for-push logic
(`_try_rebase_for_push`, `_push_to_existing_pr` master_rebase/fix_conflicts
paths) were the largest uncovered blocks in the two most important modules.
These are pure/subprocess/async functions testable with mocked subprocess calls.

**42 new tests. 5374 total tests pass. Coverage: 97.18% → 99.68%.**
