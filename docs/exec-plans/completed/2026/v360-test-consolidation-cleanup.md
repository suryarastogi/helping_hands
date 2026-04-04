# v360 — Test Consolidation & Cleanup Candidate Resolution

**Created:** 2026-04-04
**Status:** Completed
**Branch:** helping-hands/claudecodecli-121b26d5

## Objective

Resolve all `# TODO: CLEANUP CANDIDATE` markers across 6 test files by removing
redundant assertions (isinstance/positive/type-only tests that duplicate value-equality
tests) and eliminating the fully-duplicate `test_provider_build_inner.py`. Keeps all
behaviorally meaningful tests intact.

## Motivation

The cleanup candidates were identified during v135–v139 constant extraction but deferred.
They inflate test count without adding failure signal — every isinstance/positive assertion
is already implied by the value-equality test immediately above it. Removing them reduces
maintenance burden and makes test output more meaningful.

## Tasks

- [x] Remove `test_provider_build_inner.py` (9 duplicate tests)
- [x] Consolidate `test_v135_constants.py` (3 redundant tests removed)
- [x] Consolidate `test_v137_constants.py` (2 redundant tests removed)
- [x] Consolidate `test_v138_constants.py` (14 redundant tests removed)
- [x] Consolidate `test_v139_constants.py` (10 redundant tests removed)
- [x] Consolidate `test_iterative_constants.py` (6 docstring-policy tests removed)
- [x] Run full test suite — 0 failures
- [x] Update PLANS.md, INTENT.md, move plan to completed

## Plan

### 1. Remove `test_provider_build_inner.py`
All 9 tests duplicate `test_anthropic_provider.py`, `test_google_provider.py`, and
`test_litellm_provider.py`. Delete the file entirely.

### 2. Consolidate `test_v135_constants.py`
- Remove `test_constants_are_positive_integers` (duplicates value tests above)
- Remove `test_usage_log_interval_is_positive_float` (duplicates value test)
- Remove `test_usage_log_interval_is_one_hour` (duplicates exact value test)
- Remove `# TODO: CLEANUP CANDIDATE` marker

### 3. Consolidate `test_v137_constants.py`
- Keep all value-equality tests and `test_all_timeouts_are_positive` aggregate test
- Remove `test_usage_url_is_https` (implied by exact URL value test)
- Remove `test_user_agent_has_version` (implied by exact value test)
- Remove `# TODO: CLEANUP CANDIDATE` marker

### 4. Consolidate `test_v138_constants.py`
- Remove all `_is_str`, `_positive`, `_is_int`, `_not_empty` tests where a
  value-equality test exists for the same constant
- Keep `test_default_git_user_email_is_valid` (@ check is a semantic invariant)
- Keep `test_branch_prefix_ends_with_slash` (semantic invariant)
- Keep `test_file_list_preview_limit_same_as_base` (cross-module identity check)
- Remove `# TODO: CLEANUP CANDIDATE` marker

### 5. Consolidate `test_v139_constants.py`
- Remove all `_positive`, `_is_int` tests where a value-equality test exists
- Keep `test_detect_auth_failure_uses_tail_length` (behavioral test)
- Keep `test_commit_summary_shorter_than_pr_summary` (relational invariant)
- Remove `# TODO: CLEANUP CANDIDATE` marker

### 6. Consolidate `test_iterative_constants.py`
- Keep `TestReadmeCandidates`, `TestAgentDocCandidates`, `TestBackendNameConstants`
  (all meaningful)
- Remove `TestDocstringsPresent` class (stylistic policy tests, not behavioral)
- Remove `# TODO: CLEANUP CANDIDATE` marker

### 7. Verify & update docs
- Run full test suite — confirm 0 failures
- Update PLANS.md, INTENT.md
- Move plan to completed

## Completion criteria

- All 6 `# TODO: CLEANUP CANDIDATE` markers removed
- `test_provider_build_inner.py` deleted
- Full test suite passes with 0 failures
- No `CLEANUP CANDIDATE` string in any test file
- Coverage remains ≥75%

## Expected impact

- ~50 redundant tests removed
- 6 cleanup-candidate markers resolved
- 0 behavioral coverage lost
- Cleaner test output and lower maintenance burden
