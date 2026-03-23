# v290 — Player Idle/AFK Detection

**Date:** 2026-03-23
**Status:** Completed
**Scope:** Frontend multiplayer UX improvement

## Goal

Add idle/AFK detection to the multiplayer Hand World. Players who haven't
moved for a configurable timeout show a visual "zzz" indicator above their
avatar and appear as "idle" in the presence panel. This improves the
multiplayer experience by letting active players distinguish between
present and away participants.

## Changes

### 1. Constants (`constants.ts`)
- Add `IDLE_TIMEOUT_MS = 30000` (30 seconds of no movement → idle)

### 2. Hook (`useMultiplayer.ts`)
- Track `lastActivityTime` ref, updated on position/direction/walking changes
- Add `idle` boolean to awareness state, broadcast via `player` field
- Compute idle state in a 5-second interval timer
- Parse `idle` from remote player awareness updates into `RemotePlayer` type
- Expose `isLocalIdle: boolean` in return value

### 3. Types (`RemotePlayer` in useMultiplayer.ts)
- Add `idle: boolean` field to `RemotePlayer`

### 4. Component (`PlayerAvatar.tsx`)
- Accept optional `idle?: boolean` prop
- Render a floating "zzz" indicator (`idle-indicator` span) when idle

### 5. Scene (`HandWorldScene.tsx`)
- Pass `idle` prop from remote players to `PlayerAvatar`
- Show "(idle)" suffix next to idle players in presence panel

### 6. CSS (`styles.css`)
- Add `.idle-indicator` styles — floating zzz animation above avatar

### 7. Tests
- `useMultiplayer.test.tsx` — verify idle detection after timeout, reset on movement
- `PlayerAvatar.test.tsx` — verify idle indicator renders
- `HandWorldScene.test.tsx` — verify presence panel shows idle status

## Tasks

- [x] Add `IDLE_TIMEOUT_MS` constant
- [x] Add idle tracking to `useMultiplayer` hook
- [x] Add `idle` to `RemotePlayer` type
- [x] Update `PlayerAvatar` with idle indicator
- [x] Update `HandWorldScene` presence panel
- [x] Add CSS styles
- [x] Add tests
- [x] Update design doc

## Metrics
- Target: >80% branch coverage maintained
- New tests: ~6-8
