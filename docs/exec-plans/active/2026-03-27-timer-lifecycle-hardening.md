# Execution Plan: Timer Lifecycle Hardening in useMultiplayer

**Created:** 2026-03-27
**Status:** complete
**Branch:** helping-hands/claudecodecli-9f34267c
**Goal:** Fix timer/timeout memory leaks in the useMultiplayer hook — emote, chat, and cooldown timeouts are not tracked or cleaned up on deactivation, leading to potential state updates after unmount.

## Context

The useMultiplayer hook uses `setTimeout` in several callbacks (triggerEmote, sendChat) without tracking the timer handles in refs. When the hook deactivates (active=false) or unmounts, these orphaned timers can fire and attempt to update unmounted component state. The position and cursor broadcast throttles are already properly tracked via `broadcastTimerRef` and `cursorBroadcastTimerRef` — this plan extends the same pattern to emote/chat/cooldown timers.

## Problem

Five untracked `setTimeout` calls in useMultiplayer.ts:
1. Local emote display clear (`setLocalEmote(null)`)
2. Awareness emote field clear (`emote: null`)
3. Chat cooldown reset (`setChatOnCooldown(false)`)
4. Local chat display clear (`setLocalChat(null)`)
5. Awareness chat field clear (`chat: null`)

## Tasks

- [x] **Add timer refs** — `emoteTimerRef`, `emoteAwarenessTimerRef`, `chatCooldownTimerRef`, `chatDisplayTimerRef`, `chatAwarenessTimerRef`
- [x] **Track all setTimeout calls** — Store return values in refs, clear previous timer before starting new one
- [x] **Clean up timers on deactivation** — Clear all timer refs in both the `!active` branch and the effect cleanup return; also reset `localEmote`, `localChat`, and `chatOnCooldown` state on deactivation
- [x] **Add tests** — 4 new tests verifying timer cleanup on deactivation mid-emote and mid-chat
- [x] **Update documentation** — INTENT.md, daily consolidation, design doc

## Completion criteria

- All five timer leaks are fixed
- Tests verify cleanup on deactivation
- No regressions in existing 681 frontend tests

## Results

- **Frontend tests:** 681 → 685 (+4)
- **Bug fixed:** 5 orphaned `setTimeout` calls now tracked in refs and cleaned up on deactivation
- **State reset:** `localEmote`, `localChat`, `chatOnCooldown` are now explicitly reset on deactivation
