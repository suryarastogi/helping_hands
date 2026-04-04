# v349 — Interactive CLI Mode & AI Provider Types Coverage

**Created:** 2026-04-04
**Status:** Active

## Goal

Implement the last remaining product spec nice-to-have (#4: interactive mode)
and close the AI provider `types.py` test coverage gap.

## Tasks

- [x] Interactive CLI mode: `read_prompt_from_stdin()` reads from stdin when `--prompt` omitted
- [x] TTY mode prints interactive prompt, pipe mode reads silently
- [x] Empty input and Ctrl+C cause clean exit with error message
- [x] 6 new CLI tests for interactive mode
- [x] AI provider types.py test coverage: `normalize_messages()`, `AIProvider` lazy loading, `_require_sdk()`, `complete()`, `acomplete()`
- [x] 23 new provider types tests
- [x] Update INTENT.md, product spec, PLANS.md, Week-14

## Completion criteria

- `helping-hands .` (no `--prompt`) reads from stdin interactively
- `echo "fix bug" | helping-hands .` reads from pipe
- All new tests pass, no regressions
- types.py coverage ≥ 90%
- Product spec "New User Onboarding" marked fully implemented
