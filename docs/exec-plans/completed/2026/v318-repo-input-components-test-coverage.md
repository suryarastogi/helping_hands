# v318 — RepoChipInput & RepoSuggestInput Test Coverage

## Goal

Add co-located test files for the two remaining untested frontend components:
`RepoChipInput` and `RepoSuggestInput`. Both are interactive input components
with keyboard navigation, suggestion dropdowns, and filtering logic — meaningful
coverage gaps.

## Tasks

1. **RepoChipInput.test.tsx** — chip add/remove, keyboard navigation (Enter, Tab,
   comma, Backspace, ArrowUp/Down, Escape), suggestion dropdown filtering, outside
   click close, duplicate prevention, empty/whitespace handling, highlighted item
   selection, container click focus.

2. **RepoSuggestInput.test.tsx** — text input, suggestion dropdown, keyboard
   navigation (ArrowUp/Down, Enter, Escape), outside click close, filtering,
   mouse selection, dropdown visibility on focus.

3. **Docs** — update FRONTEND.md component listing, update INTENT.md, consolidate
   exec plan to completed.

## Acceptance

- All new tests pass (`npm --prefix frontend run test`)
- Coverage ≥80% for both components
- No regressions in existing 612 tests
