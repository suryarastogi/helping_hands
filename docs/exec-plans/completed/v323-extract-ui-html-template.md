# Execution Plan: Extract Inline HTML Template from app.py

**Created:** 2026-03-27
**Status:** complete
**Branch:** helping-hands/claudecodecli-9f34267c
**Goal:** Extract the ~2300-line `_UI_HTML` inline string from `app.py` to a standalone HTML template file, reducing `app.py` by ~52% and continuing the decomposition pattern from v309-v312.

## Context

`server/app.py` was 4363 lines — the single largest file in the codebase. Roughly 2293 lines (53%) was an inline HTML string (`_UI_HTML`, lines 651-2944) containing the self-contained browser UI. Extracting it to a template file:
- Makes the Python code easier to navigate
- Lets editors provide HTML syntax highlighting for the template
- Mirrors the frontend decomposition done in v309-v312 (App.tsx 3590 → 315 lines)
- Doesn't change behavior — the HTML is loaded once at module import time

## Tasks

- [x] **Create template directory** — `src/helping_hands/server/templates/`
- [x] **Extract `_UI_HTML` to `templates/ui.html`** — Moved the 2293-line HTML string to a file, kept the `__DEFAULT_SMOKE_TEST_PROMPT__` placeholder
- [x] **Add `_load_ui_template()` helper** — Reads template file, cached in module-level `_UI_HTML` variable; `_TEMPLATES_DIR` constant for directory path
- [x] **Update `home()` endpoint** — Uses loaded template (no behavior change)
- [x] **Backend tests** — 5 new tests: template file exists, valid HTML, contains placeholder, dir points correctly, home endpoint replaces placeholder
- [x] **Documentation** — Updated ARCHITECTURE.md file listing, updated Week-13, daily consolidation, INTENT.md

## Completion criteria

- `app.py` reduced from 4363 to 2085 lines (-52%) ✓
- Template file loads correctly at server startup ✓
- `GET /` still returns the same HTML with placeholder replaced ✓
- Tests cover template loading ✓
- No behavior change to the running server ✓

## Results

- **Server app tests:** 242 → 247 (+5)
- **Files changed:** `app.py`, `templates/ui.html` (new), `test_server_app.py`, `ARCHITECTURE.md`
- **app.py:** 4363 → 2085 lines (-52%)
