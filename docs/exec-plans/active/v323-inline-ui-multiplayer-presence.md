# Execution Plan: Inline HTML UI Multiplayer Presence Panel

**Created:** 2026-03-27
**Status:** complete
**Branch:** helping-hands/claudecodecli-9f34267c
**Goal:** Add a multiplayer presence panel to the inline HTML UI (`_UI_HTML` in `app.py`) so both frontend surfaces show connected players, closing the biggest sync gap between the two UIs.

## Context

The React frontend (`frontend/`) has a full multiplayer Hand World with Yjs awareness, player avatars, chat, emotes, decorations, and cursors (698 tests). The inline HTML UI (`server/app.py`) has no multiplayer awareness at all — it only shows task submission, monitoring, usage, and schedules. The FRONTEND.md documentation incorrectly claims the inline UI has "Hand world" dashboard views, but this doesn't exist.

Adding full scene parity is impractical in one step. Instead, add a **multiplayer presence panel** that polls the existing REST APIs (`/health/multiplayer`, `/health/multiplayer/players`) to show:
- Connection status (online/offline count)
- Connected player list with names, colors, positions, and idle status
- Auto-refresh every 5 seconds

This closes the biggest feature gap without requiring Yjs client-side integration in vanilla JS.

## Tasks

- [x] **Create v323 execution plan**
- [x] **Add multiplayer presence section to inline HTML** — New `<section id="multiplayer-view">` with player list, connection indicator, and auto-refresh polling
- [x] **CSS for multiplayer panel** — Player dots with colors, idle indicators, connection status badge, player cards
- [x] **JS polling logic** — IIFE fetches `/health/multiplayer/players` every 5s, renders player cards with escapeHtml, handles errors gracefully with offline status
- [x] **Fix FRONTEND.md** — Removed incorrect "Hand world" and "factory/incinerator" claims for inline UI, documented actual features including multiplayer presence panel
- [x] **Backend tests** — 2 tests in `test_server_app.py::TestHomeUI` verifying multiplayer-view section, player list, polling JS, status indicator, and badge

## Completion criteria

- Inline HTML UI shows a "Multiplayer" section with connected player list ✓
- Player names, colors, and idle status visible ✓
- Auto-refreshes every 5 seconds ✓
- Graceful degradation when multiplayer is unavailable ✓
- FRONTEND.md accurately describes both UIs ✓
- At least 1 backend test verifying the presence section exists in the HTML ✓

## Results

- **Backend tests:** 2 new tests in `test_server_app.py`
- **Files changed:** `app.py` (CSS + HTML + JS), `test_server_app.py`, `FRONTEND.md`, `INTENT.md`
