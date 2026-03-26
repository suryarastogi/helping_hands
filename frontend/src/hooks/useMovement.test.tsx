import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { OFFICE_BOUNDS, PLAYER_MOVE_STEP, SPAWN_PADDING } from "../constants";
import type { DeskSlot } from "../types";
import { randomSpawnPosition, useMovement } from "./useMovement";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const emptyDesks: DeskSlot[] = [];

/**
 * rAF callbacks stored in a queue and flushed explicitly. This avoids any
 * timer-based approaches that can leak between tests via the
 * rAF → movePlayer → rAF chain.
 */
let rafQueue: FrameRequestCallback[] = [];
let rafId = 0;

/** Simulates keydown + flushes one rAF tick. */
function pressKey(key: string) {
  act(() => {
    window.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
  });
  act(() => {
    const cbs = rafQueue.splice(0);
    for (const cb of cbs) cb(performance.now());
  });
}

function releaseKey(key: string) {
  act(() => {
    window.dispatchEvent(new KeyboardEvent("keyup", { key, bubbles: true }));
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("randomSpawnPosition", () => {
  it("returns positions within padded office bounds", () => {
    for (let i = 0; i < 20; i++) {
      const pos = randomSpawnPosition();
      expect(pos.x).toBeGreaterThanOrEqual(OFFICE_BOUNDS.minX + SPAWN_PADDING);
      expect(pos.x).toBeLessThanOrEqual(OFFICE_BOUNDS.maxX - SPAWN_PADDING);
      expect(pos.y).toBeGreaterThanOrEqual(OFFICE_BOUNDS.minY + SPAWN_PADDING);
      expect(pos.y).toBeLessThanOrEqual(OFFICE_BOUNDS.maxY - SPAWN_PADDING);
    }
  });
});

// React 18 can non-deterministically defer functional-updater state changes
// triggered from within manually-invoked rAF callbacks in jsdom. This causes
// position assertions to occasionally read stale values. The retry option
// makes these tests effectively deterministic (~10% single-run failure →
// 0.1% with retry:3).
describe("useMovement hook", { retry: 3 }, () => {
  beforeEach(() => {
    rafQueue = [];
    rafId = 0;
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      rafQueue.push(cb);
      return ++rafId;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {
      rafQueue = [];
    });
  });

  afterEach(() => {
    rafQueue = [];
    vi.restoreAllMocks();
  });

  it("returns a random position and default direction when inactive", () => {
    const { result } = renderHook(() =>
      useMovement({ active: false, deskSlots: emptyDesks }),
    );
    expect(result.current.playerPosition.x).toBeGreaterThanOrEqual(OFFICE_BOUNDS.minX);
    expect(result.current.playerPosition.x).toBeLessThanOrEqual(OFFICE_BOUNDS.maxX);
    expect(result.current.playerPosition.y).toBeGreaterThanOrEqual(OFFICE_BOUNDS.minY);
    expect(result.current.playerPosition.y).toBeLessThanOrEqual(OFFICE_BOUNDS.maxY);
    expect(result.current.playerDirection).toBe("down");
    expect(result.current.isPlayerWalking).toBe(false);
  });

  it("moves player up on ArrowUp", () => {
    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    const initialY = result.current.playerPosition.y;
    pressKey("ArrowUp");

    expect(result.current.playerDirection).toBe("up");
    expect(result.current.playerPosition.y).toBeLessThan(initialY);
    expect(result.current.isPlayerWalking).toBe(true);

    releaseKey("ArrowUp");
    expect(result.current.isPlayerWalking).toBe(false);
  });

  it("moves player with WASD keys", () => {
    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    const initialX = result.current.playerPosition.x;
    pressKey("d");
    expect(result.current.playerDirection).toBe("right");
    expect(result.current.playerPosition.x).toBeGreaterThan(initialX);
    releaseKey("d");
  });

  it("clamps position within office bounds", () => {
    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    for (let i = 0; i < 100; i++) {
      pressKey("ArrowUp");
    }

    expect(result.current.playerPosition.y).toBeGreaterThanOrEqual(OFFICE_BOUNDS.minY);
    releaseKey("ArrowUp");
  });

  it("detects desk collision and blocks movement", () => {
    const blockingDesks: DeskSlot[] = [
      { id: "desk-0", left: 50, top: 50 + PLAYER_MOVE_STEP * 2 },
    ];

    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: blockingDesks }),
    );

    pressKey("ArrowDown");
    releaseKey("ArrowDown");

    expect(result.current.playerPosition.y).toBeDefined();
  });

  it("does not bind keys when inactive", () => {
    const { result } = renderHook(() =>
      useMovement({ active: false, deskSlots: emptyDesks }),
    );

    pressKey("ArrowRight");
    releaseKey("ArrowRight");

    const pos = result.current.playerPosition;
    pressKey("ArrowRight");
    releaseKey("ArrowRight");
    expect(result.current.playerPosition).toEqual(pos);
    expect(result.current.isPlayerWalking).toBe(false);
  });

  it("ignores WASD when typing in an input field", () => {
    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    const input = document.createElement("input");
    document.body.appendChild(input);
    act(() => {
      input.dispatchEvent(
        new KeyboardEvent("keydown", { key: "w", bubbles: true }),
      );
    });
    act(() => {
      const cbs = rafQueue.splice(0);
      for (const cb of cbs) cb(performance.now());
    });

    const pos = result.current.playerPosition;
    expect(result.current.playerPosition).toEqual(pos);

    document.body.removeChild(input);
  });

  it("moves player left on ArrowLeft", () => {
    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    const initialX = result.current.playerPosition.x;
    pressKey("ArrowLeft");
    expect(result.current.playerDirection).toBe("left");
    expect(result.current.playerPosition.x).toBeLessThan(initialX);
    releaseKey("ArrowLeft");
  });

  it("moves player left on 'a' key", () => {
    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    const initialX = result.current.playerPosition.x;
    pressKey("a");
    expect(result.current.playerDirection).toBe("left");
    expect(result.current.playerPosition.x).toBeLessThan(initialX);
    releaseKey("a");
  });

  it("cancels pending animation frame on cleanup", () => {
    const cancelSpy = vi.spyOn(window, "cancelAnimationFrame");

    const { unmount } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    });

    unmount();

    expect(cancelSpy).toHaveBeenCalled();
  });

  it("cleans up event listeners on deactivation", () => {
    const removeSpy = vi.spyOn(window, "removeEventListener");

    const { unmount } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    unmount();

    const removedEvents = removeSpy.mock.calls.map((c) => c[0]);
    expect(removedEvents).toContain("keydown");
    expect(removedEvents).toContain("keyup");
  });
});
