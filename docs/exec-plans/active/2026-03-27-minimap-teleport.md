# Execution Plan: Minimap Click-to-Teleport

**Date:** 2026-03-27
**Branch:** helping-hands/claudecodecli-9f34267c
**Goal:** Add click-to-teleport to the Hand World minimap so players can quickly navigate the scene by clicking on the minimap overlay.

## Context

The minimap currently shows a read-only bird's-eye view of players and workers. Adding click-to-teleport makes navigation faster in multiplayer sessions and is a standard game UX pattern.

## Tasks

### 1. useMovement: Add teleportTo callback
- **Status:** completed
- **What:** Added `teleportTo(target: PlayerPosition)` to `UseMovementReturn`. Clamps to office bounds, checks desk collision before applying.
- **Tests added:** 3 (basic teleport, bounds clamping, desk collision blocking)

### 2. Minimap: Add click handler and onTeleport prop
- **Status:** completed
- **What:** Added optional `onTeleport` prop. Click handler converts click coordinates to scene percentages. Added `minimap-clickable` CSS class with crosshair cursor and blue hover glow.
- **Tests added:** 4 (click fires onTeleport with correct coords, clickable class present/absent, no crash without prop)

### 3. HandWorldScene: Wire onTeleport prop
- **Status:** completed
- **What:** Added `onTeleport` to `HandWorldSceneProps`, forwarded to Minimap. App.tsx passes `teleportTo` from useMovement.
- **Tests added:** 2 (clickable class present with prop, absent without)

### 4. CSS: Minimap clickable styling
- **Status:** completed
- **What:** `.minimap-clickable` overrides `pointer-events: none` to `auto`, adds crosshair cursor, blue border on hover.

### 5. Documentation updates
- **Status:** completed
- **What:** Moved v320 plan to completed, updated daily/weekly consolidation, PLANS.md, INTENT.md

## Results

- **Frontend tests:** 681 → 690 (+9)
- **Feature:** Players can click anywhere on the minimap to instantly teleport there
- **UX:** Crosshair cursor and blue glow on hover signal interactivity
