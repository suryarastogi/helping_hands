# v262: Extract _OUTPUT_FORMAT_STREAM_JSON, _normalize_preview, _extract_message_blocks

**Status:** Completed
**Created:** 2026-03-17
**Completed:** 2026-03-17

## Goal

Three self-contained DRY improvements in the Claude CLI hand stream parser:

1. **Extract `_OUTPUT_FORMAT_STREAM_JSON`** — bare string `"stream-json"` was duplicated
   in `claude.py` and `docker_sandbox_claude.py`. Extracted to a module constant in
   `claude.py` and imported from `docker_sandbox_claude.py`.

2. **Extract `_normalize_preview()` static method** — identical `text.strip().replace("\n", " ")`
   pattern duplicated in `_process_line()` for assistant text and tool result blocks.
   Extracted to a static method on `_StreamJsonEmitter`.

3. **Extract `_extract_message_blocks()` static method** — duplicate pattern of
   `event.get("message")` + `isinstance(message, dict)` check + `message.get("content", [])`
   iteration. Extracted to a static method returning an empty list for non-dict messages.

## Tasks

- [x] Create active plan
- [x] Add `_OUTPUT_FORMAT_STREAM_JSON` constant to `claude.py`
- [x] Import and use in `docker_sandbox_claude.py`
- [x] Add `_normalize_preview()` static method to `_StreamJsonEmitter`
- [x] Add `_extract_message_blocks()` static method to `_StreamJsonEmitter`
- [x] Refactor `_process_line()` to use the new helpers
- [x] Update `__all__` in `claude.py`
- [x] Add tests (23 new)
- [x] Run lint, type check, tests
- [x] Update docs

## Completion criteria

- No bare `"stream-json"` strings remain outside the constant
- No duplicate `text.strip().replace("\n", " ")` patterns
- No duplicate message extraction + content iteration patterns
- All 6133 tests pass, 272 skipped, 79% coverage
- 23 new tests cover the extracted constant and helpers

## Files touched

- `src/helping_hands/lib/hands/v1/hand/cli/claude.py` (add constant, helpers, refactor)
- `src/helping_hands/lib/hands/v1/hand/cli/docker_sandbox_claude.py` (import constant)
- `tests/test_v262_stream_json_constant_normalize_extract.py` (23 new tests)
- `tests/test_v161_all_exports.py` (update `__all__` expectations)
- `docs/PLANS.md` (index update)
