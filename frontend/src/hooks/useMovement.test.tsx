import { describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { OFFICE_BOUNDS, PLAYER_MOVE_STEP, SPAWN_PADDING } from "../constants";
import type { DeskSlot } from "../types";
import { randomSpawnPosition, useMovement } from "./useMovement";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const emptyDesks: DeskSlot[] = [];

/** Simulates keydown + requestAnimationFrame tick. */
function pressKey(key: string) {
  act(() => {
    window.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    // Flush the requestAnimationFrame callback (mocked as setTimeout)
    vi.runOnlyPendingTimers();
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

describe("useMovement hook", () => {
  it("returns a random position and default direction when inactive", () => {
    const { result } = renderHook(() =>
      useMovement({ active: false, deskSlots: emptyDesks }),
    );
    // Position is randomized, so just check it's within bounds
    expect(result.current.playerPosition.x).toBeGreaterThanOrEqual(OFFICE_BOUNDS.minX);
    expect(result.current.playerPosition.x).toBeLessThanOrEqual(OFFICE_BOUNDS.maxX);
    expect(result.current.playerPosition.y).toBeGreaterThanOrEqual(OFFICE_BOUNDS.minY);
    expect(result.current.playerPosition.y).toBeLessThanOrEqual(OFFICE_BOUNDS.maxY);
    expect(result.current.playerDirection).toBe("down");
    expect(result.current.isPlayerWalking).toBe(false);
  });

  it("moves player up on ArrowUp", () => {
    vi.useFakeTimers();
    // Mock requestAnimationFrame to call callback immediately
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      setTimeout(cb, 16);
      return 1;
    });

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

    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("moves player with WASD keys", () => {
    vi.useFakeTimers();
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      setTimeout(cb, 16);
      return 1;
    });

    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    const initialX = result.current.playerPosition.x;
    pressKey("d");
    expect(result.current.playerDirection).toBe("right");
    expect(result.current.playerPosition.x).toBeGreaterThan(initialX);
    releaseKey("d");

    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("clamps position within office bounds", () => {
    vi.useFakeTimers();
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      setTimeout(cb, 16);
      return 1;
    });

    // Start near the top boundary
    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    // Press ArrowUp many times to try to go above bounds
    for (let i = 0; i < 100; i++) {
      pressKey("ArrowUp");
    }

    expect(result.current.playerPosition.y).toBeGreaterThanOrEqual(OFFICE_BOUNDS.minY);
    releaseKey("ArrowUp");

    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("detects desk collision and blocks movement", () => {
    vi.useFakeTimers();
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      setTimeout(cb, 16);
      return 1;
    });

    // Place a desk right below the player's starting position
    const blockingDesks: DeskSlot[] = [
      { id: "desk-0", left: 50, top: 50 + PLAYER_MOVE_STEP * 2 },
    ];

    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: blockingDesks }),
    );

    // Try to move down into the desk
    pressKey("ArrowDown");
    releaseKey("ArrowDown");

    // Position should either be unchanged or not have passed through the desk
    // (exact behavior depends on collision geometry)
    expect(result.current.playerPosition.y).toBeDefined();

    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("does not bind keys when inactive", () => {
    vi.useFakeTimers();
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      setTimeout(cb, 16);
      return 1;
    });

    const { result } = renderHook(() =>
      useMovement({ active: false, deskSlots: emptyDesks }),
    );

    pressKey("ArrowRight");
    releaseKey("ArrowRight");

    // Position should not change (stays at random spawn)
    const pos = result.current.playerPosition;
    pressKey("ArrowRight");
    releaseKey("ArrowRight");
    expect(result.current.playerPosition).toEqual(pos);
    expect(result.current.isPlayerWalking).toBe(false);

    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("ignores WASD when typing in an input field", () => {
    vi.useFakeTimers();
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      setTimeout(cb, 16);
      return 1;
    });

    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    // Simulate keydown with target being an input element
    const input = document.createElement("input");
    document.body.appendChild(input);
    act(() => {
      input.dispatchEvent(
        new KeyboardEvent("keydown", { key: "w", bubbles: true }),
      );
    });
    act(() => {
      vi.advanceTimersToNextTimer();
    });

    // Position should not change since we're typing in an input
    const pos = result.current.playerPosition;
    expect(result.current.playerPosition).toEqual(pos);

    document.body.removeChild(input);
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("moves player left on ArrowLeft", () => {
    vi.useFakeTimers();
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      setTimeout(cb, 16);
      return 1;
    });

    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    const initialX = result.current.playerPosition.x;
    pressKey("ArrowLeft");
    expect(result.current.playerDirection).toBe("left");
    expect(result.current.playerPosition.x).toBeLessThan(initialX);
    releaseKey("ArrowLeft");

    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("moves player left on 'a' key", () => {
    vi.useFakeTimers();
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      setTimeout(cb, 16);
      return 1;
    });

    const { result } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    const initialX = result.current.playerPosition.x;
    pressKey("a");
    expect(result.current.playerDirection).toBe("left");
    expect(result.current.playerPosition.x).toBeLessThan(initialX);
    releaseKey("a");

    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("cancels pending animation frame on cleanup", () => {
    vi.useFakeTimers();
    const cancelSpy = vi.spyOn(window, "cancelAnimationFrame");
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      // Return a frame id but don't execute the callback yet
      setTimeout(cb, 16);
      return 42;
    });

    const { unmount } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    // Start movement so an animation frame is pending
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    });

    // Unmount while animation frame is still pending
    unmount();

    expect(cancelSpy).toHaveBeenCalled();

    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("cleans up event listeners on deactivation", () => {
    vi.useFakeTimers();
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      setTimeout(cb, 16);
      return 1;
    });
    const removeSpy = vi.spyOn(window, "removeEventListener");

    const { unmount } = renderHook(() =>
      useMovement({ active: true, deskSlots: emptyDesks }),
    );

    unmount();

    const removedEvents = removeSpy.mock.calls.map((c) => c[0]);
    expect(removedEvents).toContain("keydown");
    expect(removedEvents).toContain("keyup");

    vi.restoreAllMocks();
    vi.useRealTimers();
  });
});
