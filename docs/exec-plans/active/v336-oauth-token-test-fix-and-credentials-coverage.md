# v336 — OAuth Token Test Fix & Credentials Coverage

**Status:** completed
**Created:** 2026-03-29

## Goal

Fix 16 broken `_get_claude_oauth_token` tests caused by the addition of
`_read_claude_credentials_file()` as a first-try path — existing tests only
mock `subprocess.run` (the Keychain fallback) but the new credentials-file
reader finds a real token before the mock is reached. Add dedicated unit tests
for `_read_claude_credentials_file` itself, and fix doc structure test failures
from v335 completion.

## Tasks

- [x] Fix all `_get_claude_oauth_token` tests — mock `_read_claude_credentials_file` to return `None`
- [x] Add `_read_claude_credentials_file` unit tests: file found, file not found, invalid JSON, missing key, OSError
- [x] Add `_get_claude_oauth_token` credentials-file-first-path test
- [x] Fix doc structure tests — move v335 from active to completed in PLANS.md
- [x] Run full test suite, verify ≥75% coverage gate and 0 failures
- [x] Update INTENT.md, PLANS.md

## Results

- Fixed 16 broken tests across 3 test files by mocking `_read_claude_credentials_file`
  to return `None` so the Keychain fallback path is properly exercised
- 5 new `_read_claude_credentials_file` unit tests: valid file, missing file,
  invalid JSON, missing key, OSError
- 1 new `_get_claude_oauth_token` test verifying credentials-file-first path
  (short-circuits before Keychain)
- Moved v335 plan from active to completed
- 7631 backend tests passed, 0 failures, 96.09% coverage ✓
- Docs updated ✓

## Completion criteria

- All 18 previously failing tests pass ✓
- `_read_claude_credentials_file` has dedicated coverage ✓
- Doc structure tests pass ✓
- All existing tests still pass ✓ (7631 passed)
- Docs updated ✓
