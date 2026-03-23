# v277: Multiplayer Test Coverage & Hardening

**Status:** Completed
**Created:** 2026-03-23
**Intent:** Close multiplayer test coverage gaps identified after v273-v276

## Goal

The multiplayer Hand World feature (v273-v276) is functionally complete but has
significant test gaps — especially on the frontend (0% unit test coverage for
multiplayer logic) and several untested backend edge cases. This plan adds
semantically meaningful tests to reach >80% coverage for multiplayer code.

## Analysis

| Area | Current | Target |
|------|---------|--------|
| Backend multiplayer.py | ~75% (edge cases missing) | >85% |
| Backend multiplayer_yjs.py | ~80% (lifecycle only) | >85% |
| Frontend multiplayer utils | 0% (only wsUrl tested) | >80% |
| Frontend E2E world view | ~50% (no movement/emote) | maintain |

## Tasks

### Phase 1: Backend test hardening
- [ ] Test `handle_position()` with non-existent player_id (silent return)
- [ ] Test `handle_emote()` with non-existent player_id (already exists — verify)
- [ ] Test endpoint with unknown message type (silent skip)
- [ ] Test position update with missing optional fields (defaults used)
- [ ] Test position at exact boundary values
- [ ] Test endpoint when connect returns None (capacity rejection in endpoint)
- [ ] Test Yjs `create_yjs_app()` sets module-level globals

### Phase 2: Frontend multiplayer unit tests
- [ ] Test multiplayer constants (EMOTE_MAP, PLAYER_COLORS, EMOTE_KEY_BINDINGS)
- [ ] Test exported multiplayer types/interfaces exist
- [ ] Test buildDeskSlots collision zones match DESK_SIZE
- [ ] Test checkDeskCollision with factory/incinerator collision zones

### Phase 3: Documentation
- [ ] Update QUALITY_SCORE.md with new coverage numbers
- [ ] Update PLANS.md index
- [ ] Move plan to completed

## Dependencies
- v276 (Yjs multiplayer sync) — completed
