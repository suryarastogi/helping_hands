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

- [ ] Extract `_AUTH_ERROR_TOKENS` to `cli/base.py` with `__all__` export
- [ ] Refactor `claude.py` to import and use shared constant
- [ ] Refactor `codex.py` to import and use shared constant
- [ ] Refactor `gemini.py` to import and use shared constant
- [ ] Remove local `_AUTH_ERROR_TOKENS` from `opencode.py`, import from base
- [ ] Add docstrings to `BasicLangGraphHand.run()` and `.stream()`
- [ ] Add docstrings to `BasicAtomicHand.run()` and `.stream()`
- [ ] Add `aria-label` to inline form inputs in `App.tsx`
- [ ] Add `.catch()` to `Notification.requestPermission()` promises
- [ ] Write backend tests (constant value, imports, docstrings)
- [ ] Write frontend tests (aria-labels)
- [ ] Run all quality checks (ruff, ty, pytest, frontend lint/typecheck/test)

## Completion criteria

- All auth error tokens sourced from single `_AUTH_ERROR_TOKENS` in `cli/base.py`
- 4 iterative.py public methods have Google-style docstrings
- Inline form inputs have `aria-label` attributes
- Notification promises have `.catch()` handlers
- All quality gates pass
- Test count increases
