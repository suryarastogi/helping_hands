import { describe, expect, it } from "vitest";

import {
  CHAT_DISPLAY_MS,
  CHAT_HISTORY_MAX,
  CHAT_MAX_LENGTH,
  DESK_SIZE,
  EMOTE_DISPLAY_MS,
  EMOTE_KEY_BINDINGS,
  EMOTE_MAP,
  FACTORY_COLLISION,
  FACTORY_POS,
  INCINERATOR_COLLISION,
  INCINERATOR_POS,
  OFFICE_BOUNDS,
  PLAYER_COLORS,
  PLAYER_MOVE_STEP,
  PLAYER_SIZE,
} from "./constants";

describe("constants module", () => {
  it("exports EMOTE_DISPLAY_MS as a positive number", () => {
    expect(typeof EMOTE_DISPLAY_MS).toBe("number");
    expect(EMOTE_DISPLAY_MS).toBeGreaterThan(0);
  });

  it("exports CHAT_DISPLAY_MS as a positive number", () => {
    expect(typeof CHAT_DISPLAY_MS).toBe("number");
    expect(CHAT_DISPLAY_MS).toBeGreaterThan(0);
  });

  it("exports CHAT_MAX_LENGTH as a positive number", () => {
    expect(typeof CHAT_MAX_LENGTH).toBe("number");
    expect(CHAT_MAX_LENGTH).toBeGreaterThan(0);
  });

  it("exports CHAT_HISTORY_MAX as a positive number", () => {
    expect(typeof CHAT_HISTORY_MAX).toBe("number");
    expect(CHAT_HISTORY_MAX).toBeGreaterThan(0);
  });

  it("exports EMOTE_MAP with all four emotes", () => {
    expect(Object.keys(EMOTE_MAP)).toEqual(
      expect.arrayContaining(["wave", "celebrate", "thumbsup", "sparkle"])
    );
    for (const emoji of Object.values(EMOTE_MAP)) {
      expect(emoji.length).toBeGreaterThan(0);
    }
  });

  it("exports EMOTE_KEY_BINDINGS mapping keys 1-4", () => {
    expect(EMOTE_KEY_BINDINGS["1"]).toBe("wave");
    expect(EMOTE_KEY_BINDINGS["2"]).toBe("celebrate");
    expect(EMOTE_KEY_BINDINGS["3"]).toBe("thumbsup");
    expect(EMOTE_KEY_BINDINGS["4"]).toBe("sparkle");
  });

  it("exports PLAYER_COLORS with at least 10 entries", () => {
    expect(PLAYER_COLORS.length).toBeGreaterThanOrEqual(10);
    for (const c of PLAYER_COLORS) {
      expect(c).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });

  it("exports scene geometry constants with correct shapes", () => {
    expect(PLAYER_MOVE_STEP).toBeGreaterThan(0);
    expect(PLAYER_SIZE).toHaveProperty("width");
    expect(PLAYER_SIZE).toHaveProperty("height");
    expect(DESK_SIZE).toHaveProperty("width");
    expect(DESK_SIZE).toHaveProperty("height");
    expect(FACTORY_POS).toHaveProperty("left");
    expect(FACTORY_POS).toHaveProperty("top");
    expect(INCINERATOR_POS).toHaveProperty("left");
    expect(INCINERATOR_POS).toHaveProperty("top");
    expect(FACTORY_COLLISION).toHaveProperty("width");
    expect(INCINERATOR_COLLISION).toHaveProperty("width");
    expect(OFFICE_BOUNDS).toHaveProperty("minX");
    expect(OFFICE_BOUNDS).toHaveProperty("maxX");
  });
});
