# PRD: CLI Logging, Silent Exception Hardening & Doc Reconciliation

**Status:** Completed
**Created:** 2026-03-01
**Completed:** 2026-03-01
**Goal:** Wire the unused `--verbose` CLI flag to Python logging, replace silent exception swallowing with debug-level logging, add pyproject.toml classifiers, and reconcile documentation surfaces.

---

## Problem Statement

Several quality gaps remain after the last round of PRDs:

1. **`--verbose` flag is a no-op.** The CLI accepts `--verbose` / `-v` and stores it in `Config.verbose`, but `main()` never configures Python logging — making the flag cosmetic. Users and operators cannot enable debug output.

2. **Silent exception swallowing.** Three `except Exception: pass` blocks discard errors without any logging, making failures invisible during debugging:
   - `base.py:327` — GitHub default branch lookup silently falls back
   - `claude.py:97` — `os.geteuid()` call silently caught
   - `e2e.py:145` — GitHub default branch lookup silently returns `None`

3. **Server defensive guards lack logging.** Two Celery inspect helpers (`app.py:2169`, `app.py:2177`) catch exceptions and return sentinel values without logging — unlike the health check handlers which correctly log at warning level.

4. **pyproject.toml missing classifiers.** No Python version, framework, or topic classifiers — reduces discoverability on PyPI.

5. **Obsidian vault minor drift.** Project Log and design notes are up-to-date but could reflect this session's changes for full reconciliation.

## Success Criteria

- [x] `--verbose` / `-v` enables DEBUG-level logging output in CLI mode
- [x] All silent `except Exception: pass` blocks log at debug level instead of swallowing
- [x] Server defensive guards log at debug level before returning sentinels
- [x] pyproject.toml has standard Python classifiers
- [x] Obsidian Project Log updated with this session's work
- [x] All 488+ tests still pass; lint/format clean

## Non-Goals

- Adding a full structured logging framework (e.g., structlog)
- Changing exception handling semantics (these should still catch and continue)
- Adding logging to the server health checks (already properly logged)
- Modifying CLI behavior beyond logging setup

---

## TODO

### 1. Wire CLI `--verbose` flag to Python logging
- [x] Add `logging.basicConfig(level=...)` in `main()` based on `args.verbose`
- [x] Set DEBUG when verbose, WARNING otherwise (keeps CLI quiet by default)

### 2. Replace silent exception swallowing with debug logging
- [x] `base.py:327` — log GitHub default branch lookup failure at DEBUG
- [x] `claude.py:97` — log `geteuid()` failure at DEBUG
- [x] `e2e.py:145` — log GitHub default branch lookup failure at DEBUG

### 3. Add logging to server defensive guards
- [x] `app.py:2169` (`_safe_inspect_call`) — log at DEBUG before returning None
- [x] `app.py:2177` (`_collect_celery_current_tasks`) — log at DEBUG before returning []

### 4. Add pyproject.toml classifiers
- [x] Add Python version, framework, topic, and license classifiers

### 5. Reconcile documentation surfaces
- [x] Update Obsidian Project Log (2026-W09) with this session's changes
- [x] Verify Obsidian Architecture/Concepts accuracy against current code

---

## Activity Log

| Date | Action |
|------|--------|
| 2026-03-01 | PRD created; audit identified 5 improvement areas across CLI, server, packaging, and docs |
| 2026-03-01 | Wired `--verbose` to `logging.basicConfig()` in `cli/main.py` — DEBUG when verbose, WARNING otherwise |
| 2026-03-01 | Replaced 3 silent `except Exception: pass` blocks with `logger.debug()` in `base.py`, `claude.py`, `e2e.py` |
| 2026-03-01 | Added debug logging to server Celery inspect defensive guards in `app.py` |
| 2026-03-01 | Added 10 PyPI classifiers to `pyproject.toml` (Python 3.12–3.14, Apache-2.0, topics, typing) |
| 2026-03-01 | Updated Obsidian Project Log (W09), Project todos, and AGENT.md recurring decisions |
| 2026-03-01 | All 488 tests pass, lint/format clean. PRD complete — moving to completed/ |
