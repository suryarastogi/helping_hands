# v339 — Meta Tools Coverage Hardening

**Status:** Completed
**Created:** 2026-03-30
**Theme:** Close testable coverage gaps in `meta/tools/` modules

## Goal

Raise coverage for the meta tools layer:
- `web.py` 81% → 98% (HTTP error handling, response parsing, related topics, browse edge cases)
- `filesystem.py` 92% → 100% (type check, large file, mkdir OSError)

## Tasks

- [x] Add `web.py` tests: `_raise_url_error` HTTP vs URL paths, `_require_http_url` scheme/netloc validation, `_decode_bytes` UTF-16 fallback, `_as_string_keyed_dict` edge cases, `_extract_related_topics` nested recursion, `browse_url` non-HTML content, search result deduplication/filtering, HTTPError/URLError catch blocks
- [x] Add `filesystem.py` tests: non-string rel_path TypeError, large file rejection, `mkdir_path` OSError
- [x] Run tests, verify coverage improvement
- [x] Update docs (INTENT.md, daily consolidation)

## Completion criteria

- [x] All new tests pass — 6580 passed, 0 failures
- [x] No regressions in existing tests
- [x] `web.py` coverage ≥ 95% — achieved 98%
- [x] `filesystem.py` coverage ≥ 95% — achieved 100%

## Results

- **38 new tests** in `test_meta_tools_web_gaps.py` (web.py coverage gaps)
- **4 new tests** in `test_filesystem.py` (filesystem.py coverage gaps)
- **6580 backend tests passed**, 75.84% overall coverage
- `web.py`: 81% → 98% (only `pragma: no cover` defensive fallback remains)
- `filesystem.py`: 92% → 100%
