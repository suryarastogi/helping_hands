# v231 — Type annotation fix, OpenCode auth, CLI prompt validation

**Created:** 2026-03-16
**Status:** Completed

## Goal

Three self-contained improvements across CLI hands and iterative backends:

1. **Fix `_input_schema` type annotation** — Remove `# type: ignore[assignment]`
   in `atomic.py` and `iterative.py` by changing `type[Any]` to `type[Any] | None`,
   with a `RuntimeError` guard in `_make_input()`.
2. **Add `_describe_auth()` to OpenCodeCLIHand** — For consistency with Claude,
   Gemini, Goose, and Codex hands, OpenCode now reports auth status based on
   the resolved model's provider prefix.
3. **Add prompt validation to `_TwoPhaseCLIHand.run()`/`stream()`** — Reject
   empty/whitespace prompts at the public API boundary via `require_non_empty_string`.

## Tasks

- [x] Create this plan
- [x] Fix `_input_schema` type annotation in atomic.py and iterative.py
- [x] Add `_describe_auth()` override to OpenCodeCLIHand
- [x] Add `require_non_empty_string(prompt, "prompt")` to `run()`/`stream()`
- [x] Add tests for all three changes
- [x] Run lint, format, type check, pytest
- [x] Update docs

## Completion criteria

- All changes have full branch coverage tests
- Lint, format, type check pass
- Full test suite passes with no regressions

## Files changed

- `src/helping_hands/lib/hands/v1/hand/atomic.py`
- `src/helping_hands/lib/hands/v1/hand/iterative.py`
- `src/helping_hands/lib/hands/v1/hand/cli/opencode.py`
- `src/helping_hands/lib/hands/v1/hand/cli/base.py`
- `tests/test_v231_type_annotation_opencode_auth_prompt_validation.py`
- `tests/test_v161_all_exports.py` (updated `__all__` count/private assertions)
