# v369 — Filesystem & Web Type Guards

**Created:** 2026-04-05
**Status:** Active
**Theme:** Add missing `isinstance` type guards to security-boundary functions

## Context

Two functions that handle untrusted input lack explicit type guards:

1. `resolve_repo_target()` in `filesystem.py` accepts `repo_root: Path` but has no
   `isinstance` guard. If called with a string, int, or None, `repo_root.resolve()`
   raises `AttributeError` instead of a clear `TypeError`. The companion parameter
   `rel_path` already has a type guard in `normalize_relative_path()`.

2. `_decode_bytes()` in `web.py` accepts `payload: bytes` but has no `isinstance`
   guard. If called with a string or None, `payload.decode()` raises
   `AttributeError` instead of a clear `TypeError`.

Both follow the same pattern fixed in v368 (`validate_repo_value`).

## Tasks

- [x] Add `isinstance` type guard to `resolve_repo_target()` raising `TypeError`
- [x] Add `isinstance` type guard to `_decode_bytes()` raising `TypeError`
- [x] Add tests for `resolve_repo_target()` type guard (str, int, None — 3 tests)
- [x] Add tests for `_decode_bytes()` type guard (str, int, None — 3 tests)
- [x] Update docs (PLANS.md, INTENT.md, Week-14)

## Completion criteria

- `resolve_repo_target("not-a-path", "file.txt")` raises `TypeError`, not `AttributeError`
- `_decode_bytes("not bytes")` raises `TypeError`, not `AttributeError`
- All existing tests still pass
