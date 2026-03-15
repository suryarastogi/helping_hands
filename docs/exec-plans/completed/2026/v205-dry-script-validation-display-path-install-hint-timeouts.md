# v205 — DRY script validation, display path, install hint, timeout constants

**Status:** completed
**Date:** 2026-03-15

## Changes

1. **Extract `_validate_script_path` in command.py** — shared helper replaces
   duplicated 5-line script-not-found / is-a-directory validation in both
   `run_python_script` and `run_bash_script`.

2. **Extract `_display_path` in filesystem.py** — shared helper replaces 4×
   inline `target.relative_to(root).as_posix()` calls across `read_text_file`,
   `write_text_file`, and `mkdir_path`.

3. **DRY `install_hint` in AI provider error messages** — all 5 provider
   `_build_inner()` methods now use `self.install_hint` in the RuntimeError
   message instead of hardcoding the install command string (anthropic, openai,
   google, litellm, ollama).

4. **DRY timeout constants to `server/constants.py`** — `KEYCHAIN_TIMEOUT_S`
   and `USAGE_API_TIMEOUT_S` moved from duplicated local definitions in both
   `app.py` and `celery_app.py` to the shared constants module.

## Tests

27 new tests (23 passed, 4 skipped without fastapi/celery):
- `TestValidateScriptPath` (7 tests): helper + delegation from both callers
- `TestDisplayPath` (7 tests): helper + integration with read/write/mkdir
- `TestProviderInstallHintInError` (5 tests): all 5 providers
- `TestSharedTimeoutConstants` (4 tests): value and type assertions
- `TestTimeoutConstantsImported` (4 tests, skipped): import consistency

Full suite: 4936 passed, 212 skipped.
