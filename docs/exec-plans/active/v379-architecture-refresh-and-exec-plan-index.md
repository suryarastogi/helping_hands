# v379 — ARCHITECTURE.md Refresh & Exec-Plan Index

**Created:** 2026-04-05
**Status:** Active

## Goal

Update the stale `ARCHITECTURE.md` (last updated 2026-03-07) to reflect the
current state of the codebase after ~30 days of active development. Add
structural accuracy tests. Create `docs/exec-plans/index.md` for navigation.

## Context

Since the last ARCHITECTURE.md update, numerous modules and CLI features have
been added:

- `cli/doctor.py` — environment prerequisite checker
- `lib/validation.py` — input validation utilities
- `lib/github_url.py` — shared GitHub URL/clone helpers
- `server/token_helpers.py` — extracted token/credential helpers
- `server/constants.py` — shared server constants
- `server/multiplayer_yjs.py` — multiplayer Yjs WebSocket
- `server/grill.py` — interactive planning (Grill Me)
- CLI flags: `--version`, `--list-backends`, `--list-tools`
- `DevinCLIHand`, `OpenCodeCLIHand` added to hand table
- Task result normalization section added

## Tasks

- [x] Create active plan v379
- [x] Update ARCHITECTURE.md with new modules, CLI features, and accurate file paths
- [x] Add structural accuracy tests (verify mentioned files exist)
- [x] Create docs/exec-plans/index.md
- [x] Update PLANS.md, INTENT.md, Week-14 consolidation

## Completion criteria

- All 7 new tests in `test_architecture_accuracy.py` pass
- Every path in the ARCHITECTURE.md "Key file paths" table exists on disk
- Every non-init source module is mentioned in ARCHITECTURE.md
- `docs/exec-plans/index.md` exists with weekly consolidation links
- PLANS.md, INTENT.md, and Week-14 updated with v379 entry

## Files changed

- `ARCHITECTURE.md`
- `docs/exec-plans/active/v379-architecture-refresh-and-exec-plan-index.md`
- `docs/exec-plans/index.md`
- `tests/test_architecture_accuracy.py`
- `docs/PLANS.md`
- `INTENT.md`
- `docs/exec-plans/completed/2026/Week-14.md`
