# v371 — Enrich `--list-backends` with Enabled Status

**Created:** 2026-04-05
**Status:** Completed
**Theme:** CLI discoverability — show both availability and enabled/disabled status per backend

## Context

`--list-backends` (v370) shows whether each backend's binary or Python extra is
installed, but doesn't indicate whether the backend is **enabled** via its
`*_ENABLED` env var. Users seeing `[+] basic-langgraph` may try to use it
only to discover it's disabled at the server level. Adding enabled status
gives a complete diagnostic picture.

Also, the `_check_backend_available()` fallback (line 125) silently returns
`True, "available"` for backends not mapped in either `_BACKEND_CLI_TOOL` or
`_BACKEND_PYTHON_EXTRA`. While the mapping coverage test catches this at test
time, the runtime fallback should log a warning.

## Tasks

- [x] Add `is_backend_enabled(backend)` public API in factory module returning `(bool, str)` with enabled/disabled and env var name
- [x] Enrich `list_backends()` output to show `enabled` / `disabled (HELPING_HANDS_*_ENABLED)` alongside availability
- [x] Add warning in `_check_backend_available()` default fallback for unmapped backends
- [x] Add tests for `is_backend_enabled()` — all-enabled default, single enabled, single disabled, unknown backend, all known backends
- [x] Add tests for enriched `list_backends()` output format — disabled shows [-], enabled shows [+], footer count
- [x] Add test for unmapped backend warning via caplog
- [x] Update PLANS.md, INTENT.md, daily consolidation

## Completion criteria

- `--list-backends` output includes both availability and enabled status
- Enabled/disabled is clearly distinguishable from available/unavailable
- When no `*_ENABLED` env vars are set, all show as "enabled (default)"
- Tests pass, ruff clean
