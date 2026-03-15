# v193 — DRY auth error tokens, iterative docstrings, frontend a11y

**Status:** completed
**Created:** 2026-03-15
**Branch:** helping-hands/claudecodecli-bfc17b62

## Goal

Three self-contained improvements:

1. **DRY auth error tokens** — Extract shared `_AUTH_ERROR_TOKENS` constant to
   `cli/base.py` and import in `claude.py`, `codex.py`, `gemini.py` (matching
   `opencode.py` pattern). Eliminates 4× duplicated auth detection strings.

2. **Iterative docstrings** — Add Google-style docstrings to the 4 remaining
   undocumented public methods: `BasicLangGraphHand.run()`,
   `BasicLangGraphHand.stream()`, `BasicAtomicHand.run()`,
   `BasicAtomicHand.stream()`.

3. **Frontend accessibility** — Add `aria-label` attributes to inline form
   inputs (repo, prompt) and `.catch()` handlers to unhandled
   `Notification.requestPermission()` promises.

## Tasks

- [x] Extract `_AUTH_ERROR_TOKENS` to `cli/base.py` with `__all__` export
- [x] Refactor `claude.py` to import and use shared constant
- [x] Refactor `codex.py` to import and use shared constant
- [x] Refactor `gemini.py` to import and use shared constant
- [x] Remove local `_AUTH_ERROR_TOKENS` from `opencode.py`, import from base
- [x] Add docstrings to `BasicLangGraphHand.run()` and `.stream()`
- [x] Add docstrings to `BasicAtomicHand.run()` and `.stream()`
- [x] Add `aria-label` to inline form inputs in `App.tsx`
- [x] Add `.catch()` to `Notification.requestPermission()` promises
- [x] Write backend tests (constant value, imports, docstrings)
- [x] Write frontend tests (aria-labels)
- [x] Run all quality checks (ruff, ty, pytest, frontend lint/typecheck/test)

## Completion criteria

- All auth error tokens sourced from single `_AUTH_ERROR_TOKENS` in `cli/base.py`
- 4 iterative.py public methods have Google-style docstrings
- Inline form inputs have `aria-label` attributes
- Notification promises have `.catch()` handlers
- All quality gates pass
- Test count increases
