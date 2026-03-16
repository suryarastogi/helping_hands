# v225 — Validation type guards, _normalize_args container check, search_web DRY

**Date:** 2026-03-16
**Status:** Completed

## Goal

Harden shared validation helpers with type guards and consolidate inline validation in web.py with centralized helpers.

1. Add `isinstance(value, str)` type guard to `require_non_empty_string()` in `validation.py`
2. Add `isinstance(value, int)` type guard (rejecting `bool`) to `require_positive_int()` in `validation.py`
3. Add `isinstance(args, (list, tuple))` container type guard to `_normalize_args()` in `command.py`
4. Replace inline query validation in `search_web()` and `_require_http_url()` with `require_non_empty_string()`

## Tasks

- [x] Add type guard to `require_non_empty_string()` in `validation.py`
- [x] Add type guard to `require_positive_int()` in `validation.py`
- [x] Add container type guard to `_normalize_args()` in `command.py`
- [x] Use `require_non_empty_string()` in `search_web()` and `_require_http_url()`
- [x] Write tests for all new validation paths
- [x] Run ruff + ty + pytest
- [x] Fix pre-existing mock bug in `test_hand_base_statics.py` (used `html_url` instead of `url`)

## Changes

### `src/helping_hands/lib/validation.py`

- **`require_non_empty_string()`**: Added `isinstance(value, str)` type guard raising `TypeError` for non-string inputs. Previously, passing `None` caused `AttributeError` on `.strip()`.
- **`require_positive_int()`**: Added `isinstance(value, bool) or not isinstance(value, int)` type guard raising `TypeError` for non-int inputs. `bool` is explicitly rejected (Python `bool` subclasses `int`).

### `src/helping_hands/lib/meta/tools/command.py`

- **`_normalize_args()`**: Added `isinstance(args, (list, tuple))` container type guard. Previously, passing a `dict` would silently iterate keys; passing a `set` would silently iterate values. Now raises `TypeError` for non-list/tuple. Also changed `if not args:` to `if args is None:` to prevent empty-list falsy check from interfering with the new type guard.

### `src/helping_hands/lib/meta/tools/web.py`

- **`search_web()`**: Replaced inline `query.strip()` + `if not normalized_query` with `require_non_empty_string(query, "query")`. Gets type guard for free.
- **`_require_http_url()`**: Replaced inline `url.strip()` + `if not candidate` with `require_non_empty_string(url, "url")`. Gets type guard for free. Updated docstring to document `TypeError`.
- Added import of `require_non_empty_string` from `validation.py`.

### Tests

- **`tests/test_v225_validation_type_guards_normalize_args.py`**: 35 tests across 6 classes:
  - `TestRequireNonEmptyStringTypeGuard` (9): None, int, bool, list, dict, float, bytes, valid string, empty string
  - `TestRequirePositiveIntTypeGuard` (8): True, False, string, float, None, list, valid int, zero
  - `TestNormalizeArgsContainerGuard` (11): dict, set, string, int, generator, None, empty list/tuple, valid list/tuple, non-string element
  - `TestWebUsesRequireNonEmptyString` (4): source consistency for search_web and _require_http_url
  - `TestValidationSourceConsistency` (3): isinstance checks present in source
  - `TestNormalizeArgsSourceConsistency` (1): isinstance check present in source

### Bug fixes

- **`tests/test_web_helpers.py`**: Updated error message match from `"non-empty"` to `"must not be empty"` (aligned with `require_non_empty_string` message format).
- **`tests/test_web_edge_cases.py`**: Same error message alignment.
- **`tests/test_hand_base_statics.py`**: Fixed 3 test mocks using `html_url=` (wrong attribute) → `url=` (matches `PRResult.url`). Previously passed because MagicMock auto-generates attributes; now caught by type guard.

## Completion criteria

- `require_non_empty_string(None, "x")` raises `TypeError` ✓
- `require_positive_int("5", "x")` raises `TypeError` ✓
- `require_positive_int(True, "x")` raises `TypeError` ✓
- `_normalize_args({"a": 1})` raises `TypeError` ✓
- `search_web()` and `_require_http_url()` use centralized `require_non_empty_string()` ✓
- All existing tests pass, new tests cover all changes ✓

## Results

- **35 new tests**
- **5439 passed, 219 skipped**, coverage 78.78%
