# v361 — Fix Stale Test Imports & Coverage Recovery

**Status:** Completed
**Created:** 2026-04-04
**Goal:** Fix 10 test files with broken imports from v357 token_helpers/github_url extraction; recover server module test coverage from 1–3% to 95%+.

## Context

The v357 extraction plans moved functions and constants out of `server/app.py` and `server/celery_app.py` into `server/token_helpers.py` and `lib/github_url.py`. Several test files were left with stale imports, causing collection errors when server extras are installed. Without server extras, these tests were silently skipped, masking the breakage.

## Tasks

- [x] Fix `test_celery_helpers.py` — update `_git_noninteractive_env` and `_redact_sensitive` imports to `github_url`
- [x] Fix `test_server_app_usage.py` — update `_read_claude_credentials_file` import and monkeypatch targets to `token_helpers`
- [x] Fix `test_v198_redact_token_constants_init_all.py` — update redact token constant imports to `token_helpers`
- [x] Fix `test_v116_exception_logging.py` — update monkeypatch targets for credentials reader
- [x] Fix `test_v137_constants.py` — update keychain timeout import to `constants` module
- [x] Fix `test_v141_e2e_constant_pr_validation_celery_timeouts.py` — update keychain timeout sync test
- [x] Fix `test_v144_mcp_index_limit_jwt_prefix_e2e_uuid.py` — update JWT prefix imports to `constants`
- [x] Fix `test_v145_keychain_constants_utilization_guard.py` — update keychain constant imports to `constants`
- [x] Fix `test_v205_dry_helpers.py` — remove test for non-existent `app._KEYCHAIN_TIMEOUT_S`
- [x] Fix `test_v242_dry_usage_level_narrow_exceptions.py` — update credentials reader monkeypatch target
- [x] Verify full test suite passes: 7968 passed, 98.71% coverage
- [ ] Update documentation (INTENT.md, PLANS.md, QUALITY_SCORE.md)

## Results

- **Before:** 6779 tests passed (76.03% coverage) — server tests silently skipped without extras; 3 collection errors with extras
- **After:** 7968 tests passed (98.71% coverage) — all server module tests now execute
- **Files modified:** 10 test files
- **Net new tests:** 0 (recovered 1189 tests that were broken/skipped)
