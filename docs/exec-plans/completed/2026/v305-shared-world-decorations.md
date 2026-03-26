# v305 — Shared World Decorations via Y.Map

**Status:** Completed
**Created:** 2026-03-26

## Goal

Add persistent shared decorations to the multiplayer Hand World using Yjs
Y.Map document state (not just awareness). Players can place emoji markers in
the scene that all connected players see in real-time. This exercises the
persistent Y.Doc capability that has been unused since the Yjs migration.

## Design

### Data model

Each decoration is a Y.Map entry keyed by a unique ID:

```typescript
type WorldDecoration = {
  id: string;
  emoji: string;
  x: number;       // % of scene
  y: number;       // % of scene
  placedBy: string; // player name
  color: string;    // player colour
  placedAt: number; // timestamp
};
```

### Frontend changes

1. **constants.ts** — `DECORATION_EMOJIS` palette, `MAX_DECORATIONS` cap (20)
2. **types.ts** — `WorldDecoration` type
3. **useMultiplayer.ts** —
   - Create `Y.Map<string>` named `"decorations"` in Y.Doc
   - Observe map changes → `decorations` state array
   - Expose `placeDecoration(emoji, x, y)` and `clearDecorations()` callbacks
   - Return `decorations` array in hook result
4. **HandWorldScene.tsx** —
   - Render decorations as positioned emoji elements
   - Double-click on scene → place decoration at click position
   - Decoration toolbar (emoji palette) in Factory Floor panel
   - Clear all button (only when decorations exist)
5. **Tests** — hook decoration state, scene rendering, place/clear interactions

### Backend changes

None — `pycrdt-websocket` already syncs the full Y.Doc including Y.Map.

## Result

- `WorldDecoration` type in `types.ts`, `DECORATION_EMOJIS` and `MAX_DECORATIONS` in `constants.ts`
- Y.Map `"decorations"` in `useMultiplayer` hook with observe/sync/place/clear
- Decoration toolbar in Factory Floor panel with 8 emoji palette, count, clear button
- Double-click scene to place selected emoji at click position
- Positioned emoji elements with pop animation and drop shadow
- 16 new tests (6 hook, 10 scene) — 482 frontend tests total (up from 466)
- No backend changes needed (pycrdt-websocket syncs Y.Map automatically)
