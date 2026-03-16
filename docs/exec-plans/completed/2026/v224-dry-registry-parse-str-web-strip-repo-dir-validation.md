# v224 — DRY registry _parse_required_str, web.py strip dedup, repo_dir validation

**Date:** 2026-03-16
**Status:** Completed

## Goal

Three self-contained improvements:

1. Extract `_parse_required_str()` helper in `registry.py` replacing 4× duplicated `isinstance(X, str) or not X.strip()` pattern
2. Pre-compute `.strip()` values in `web.py` `_extract_related_topics()` (redundant 3× `text.strip()` + 2× `url.strip()`)
3. Add `repo_dir.is_dir()` validation in `_configure_authenticated_push_remote()` (base.py)

## Tasks

- [x] Add `_parse_required_str()` to registry.py and replace 4 inline validations
- [x] DRY `.strip()` calls in `_extract_related_topics()` in web.py
- [x] Add `repo_dir.is_dir()` precondition in `_configure_authenticated_push_remote`
- [x] Write tests for all new validation paths
- [x] Run ruff + ty + pytest

## Changes

### `src/helping_hands/lib/meta/tools/registry.py`

- **`_parse_required_str()`**: New helper that extracts and validates a required non-empty string from a tool payload dict. Replaces 4× inline `if not isinstance(X, str) or not X.strip()` patterns.
- **`_run_python_code()`**: Replaced inline validation with `_parse_required_str(payload, key="code")`.
- **`_run_python_script()`**: Replaced inline validation with `_parse_required_str(payload, key="script_path")`.
- **`_run_web_search()`**: Replaced inline validation with `_parse_required_str(payload, key="query")`.
- **`_run_web_browse()`**: Replaced inline validation with `_parse_required_str(payload, key="url")`.

### `src/helping_hands/lib/meta/tools/web.py`

- **`_extract_related_topics()`**: Pre-compute `text = raw_text.strip()` and `url = raw_url.strip()` once each, eliminating redundant 3× `text.strip()` + 2× `url.strip()` calls.

### `src/helping_hands/lib/hands/v1/hand/base.py`

- **`_configure_authenticated_push_remote()`**: Added `repo_dir.is_dir()` precondition check before git operations. Updated docstring Raises section.

### Tests

- **`tests/test_v224_dry_parse_str_web_strip_repo_dir.py`**: 24 tests across 4 classes:
  - `TestParseRequiredStr` (9): missing key, None, non-string, empty, whitespace, valid, whitespace-preserving, bool, list
  - `TestParseRequiredStrUsedInRunners` (4): source consistency checks for all 4 runner wrappers
  - `TestExtractRelatedTopicsStrip` (7): whitespace stripping, empty text/url, non-string types, multiple items, pre-computed strip source check
  - `TestConfigureAuthPushRemoteRepoDirValidation` (4): nonexistent path, file path, valid dir, source check

## Completion criteria

- `_parse_required_str` used in `_run_python_code`, `_run_python_script`, `_run_web_search`, `_run_web_browse`
- `_extract_related_topics` calls `.strip()` once per variable
- `_configure_authenticated_push_remote` rejects non-directory `repo_dir`
- All existing tests pass, new tests cover all changes

## Results

- **24 new tests**
- **5403 passed, 219 skipped**, coverage 78.76%
