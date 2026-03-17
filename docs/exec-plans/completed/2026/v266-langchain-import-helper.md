# v266: Extract _require_langchain_class() helper

**Status:** Completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Goal

Extract a `_require_langchain_class()` helper in `model_provider.py` to
deduplicate the 3 identical `try: from X import Y except ModuleNotFoundError:
raise RuntimeError(...)` blocks in `build_langchain_chat_model()`.

The `_make_input()` dedup (atomic.py vs iterative.py) was evaluated but
skipped — the two classes don't share a common base, so a mixin for 3 lines
would be over-engineering.

## Tasks

- [x] Create active plan
- [x] Add `_require_langchain_class()` helper in `model_provider.py`
- [x] Refactor 3 langchain import blocks to use the helper
- [x] Add tests for all changes (11 new tests)
- [x] Run lint, type check, tests
- [x] Update docs, move plan to completed

## Completion criteria

- No duplicate ModuleNotFoundError blocks in `build_langchain_chat_model()`
- All tests pass, lint/format clean
- 11 new tests cover `_require_langchain_class()` and integration

## Files touched

- `src/helping_hands/lib/hands/v1/hand/model_provider.py` (add helper, refactor 3 blocks)
- `tests/test_v266_langchain_import_helper.py` (11 new tests)
- `tests/test_v159_all_exports.py` (update `__all__` count 10→11, add to allowed private)
- `docs/PLANS.md` (index update)
