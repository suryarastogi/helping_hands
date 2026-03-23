/**
 * Shared constants for Hand World scene layout, player physics, and
 * multiplayer emotes.
 *
 * Extracted from App.tsx so that hooks and components can import these
 * without depending on the root component module.
 */

// ---------------------------------------------------------------------------
// Emotes
// ---------------------------------------------------------------------------

/** How long (ms) an emote bubble is displayed above a player. */
export const EMOTE_DISPLAY_MS = 2000;

/** How long (ms) a chat bubble is displayed above a player. */
export const CHAT_DISPLAY_MS = 4000;

/** Maximum length of a chat message. */
export const CHAT_MAX_LENGTH = 120;

/** Mapping from emote name to emoji character. */
export const EMOTE_MAP: Record<string, string> = {
  wave: "\u{1F44B}",
  celebrate: "\u{1F389}",
  thumbsup: "\u{1F44D}",
  sparkle: "\u{2728}",
};

/** Keyboard shortcuts for triggering emotes (keys 1–4). */
export const EMOTE_KEY_BINDINGS: Record<string, string> = {
  "1": "wave",
  "2": "celebrate",
  "3": "thumbsup",
  "4": "sparkle",
};

// ---------------------------------------------------------------------------
// Player colours
// ---------------------------------------------------------------------------

/** Player avatar colour palette — indexed by Yjs clientID. */
export const PLAYER_COLORS = [
  "#e11d48", "#2563eb", "#16a34a", "#d97706", "#7c3aed",
  "#0891b2", "#dc2626", "#4f46e5", "#059669", "#c026d3",
];

// ---------------------------------------------------------------------------
// Scene geometry
// ---------------------------------------------------------------------------

/** Pixels (as % of scene) a player moves per key-press tick. */
export const PLAYER_MOVE_STEP = 1.2;

/** Player bounding-box size (% of scene). */
export const PLAYER_SIZE = { width: 3.5, height: 4 };

/** Desk bounding-box size (% of scene). */
export const DESK_SIZE = { width: 8, height: 7 };

/** Factory entrance position (% of scene). */
export const FACTORY_POS = { left: 8, top: 52 };

/** Incinerator exit position (% of scene). */
export const INCINERATOR_POS = { left: 92, top: 52 };

/** Factory collision box (% of scene). */
export const FACTORY_COLLISION = { left: 2, top: 42, width: 14, height: 20 };

/** Incinerator collision box (% of scene). */
export const INCINERATOR_COLLISION = { left: 84, top: 42, width: 14, height: 20 };

/** Walkable area bounds (% of scene). */
export const OFFICE_BOUNDS = { minX: 4, maxX: 96, minY: 6, maxY: 92 };
