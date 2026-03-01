# PRD: Code Quality, Export Completeness & Cross-Surface Doc Reconciliation

## Problem Statement

After a large sprint of docstring, test, and export hardening, several small but actionable gaps remain across the codebase: module-level import hygiene in CLI hands, incomplete `__all__` exports in `server/app.py`, `__all__` placement convention in `lib/meta/skills/__init__.py`, missing docstrings on a handful of CLI hand overrides, and cross-surface documentation drift between README.md, CLAUDE.md, and the Obsidian vault.

## Success Criteria

- All CLI hand modules use module-level `import os` (no method-body imports)
- `server/app.py` `__all__` includes all public Pydantic models
- `lib/meta/skills/__init__.py` `__all__` is moved to the conventional top-of-module position
- Missing docstrings added to `CodexCLIHand._native_cli_auth_env_names()`, `GooseCLIHand._describe_auth()`, `GooseCLIHand._resolve_cli_model()`, and `_TwoPhaseCLIHand._no_change_error_after_retries()` base method
- README.md includes `ty check` command matching CLAUDE.md
- CLAUDE.md includes `npm --prefix frontend run coverage` matching README.md
- Obsidian vault reflects updated module export count, test count, and any new conventions

## Non-Goals

- Adding new tests (separate PRD territory)
- Changing any runtime behavior
- Refactoring hand architecture

## TODO

- [x] **P1: Fix module-level imports** — Move `import os` from method bodies to top of `goose.py` and `gemini.py`
- [x] **P2: Complete `server/app.py` `__all__`** — Add `CurrentTask`, `CurrentTasksResponse`, `WorkerCapacityResponse`, `ServerConfig`, `ScheduleRequest`, `ScheduleResponse`, `ScheduleListResponse`, `ScheduleTriggerResponse`, `CronPresetsResponse`, `ServiceHealthResponse`
- [x] **P3: Relocate `skills/__init__.py` `__all__`** — Move from bottom (line 322) to top, after imports
- [x] **P4: Add missing CLI hand docstrings** — `CodexCLIHand._native_cli_auth_env_names()`, `GooseCLIHand._describe_auth()`, `GooseCLIHand._resolve_cli_model()`, `_TwoPhaseCLIHand._no_change_error_after_retries()` base
- [x] **P5: Reconcile README ↔ CLAUDE.md** — Add `ty check` to README, add `coverage` to CLAUDE.md
- [x] **P6: Reconcile Obsidian vault** — Update module export counts, test assertions, and new conventions in Architecture.md, AGENT.md, Completed PRDs.md, Project todos.md

## Activity Log

- **2026-03-01T00:00Z** — PRD created, analysis complete, 6 TODO items identified
- **2026-03-01T00:01Z** — P1 complete: moved `import os` to module level in goose.py and gemini.py
- **2026-03-01T00:02Z** — P2 complete: expanded server/app.py `__all__` with 10 public models
- **2026-03-01T00:03Z** — P3 complete: relocated skills/__init__.py `__all__` to top after imports
- **2026-03-01T00:04Z** — P4 complete: added 4 missing docstrings to CLI hand overrides and base
- **2026-03-01T00:05Z** — P5 complete: README.md gets `ty check`, CLAUDE.md gets `coverage`
- **2026-03-01T00:06Z** — P6 complete: Obsidian Architecture.md, AGENT.md, Completed PRDs updated
- **2026-03-01T00:07Z** — PRD moved to completed/
