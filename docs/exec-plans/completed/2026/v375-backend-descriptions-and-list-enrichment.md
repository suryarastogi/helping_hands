# v375 — Backend Descriptions & `--list-backends` Enrichment

**Status:** Completed
**Created:** 2026-04-05

## Problem

`--list-backends` shows availability and enabled status but no description of
what each backend actually does. New users must read docs to understand the
difference between `claudecodecli`, `basic-langgraph`, and `goose`.

## Tasks

- [x] Add `BACKEND_DESCRIPTIONS` dict to `factory.py` mapping each backend to a
  short human-readable description
- [x] Add `_validate_backend_descriptions_consistency()` module-level check
- [x] Export `get_backend_description()` public API
- [x] Enrich `list_backends()` in `cli/main.py` to include descriptions
- [x] Add tests: structural consistency, known/unknown lookup, output assertions
- [x] Fix pre-existing test expecting old output format
- [x] Update docs: INTENT.md, daily consolidation, Week-14, move plan to completed

## Completion criteria

- `--list-backends` output includes a brief description for every backend
- `BACKEND_DESCRIPTIONS` stays in sync with `SUPPORTED_BACKENDS` via runtime check
- All new code has test coverage
