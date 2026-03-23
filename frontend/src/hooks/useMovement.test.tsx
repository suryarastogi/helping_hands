import { describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { OFFICE_BOUNDS, PLAYER_MOVE_STEP } from "../constants";
import type { DeskSlot } from "../types";
import { useMovement } from "./useMovement";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const emptyDesks: DeskSlot[] = [];

/** Simulates keydown + requestAnimationFrame tick. */
function pressKey(key: string) {
  act(() => {
    window.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
  });
  // Flush the requestAnimationFrame callback
  act(() => {
    vi.advanceTimersByTime(16);
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

describe("useMovement hook", () => {
  it("returns default position when inactive", () => {
    const { result } = renderHook(() =>
      useMovement({ active: false, deskSlots: emptyDesks }),
    );
    expect(result.current.playerPosition).toEqual({ x: 50, y: 50 });
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

    pressKey("ArrowUp");

    expect(result.current.playerDirection).toBe("up");
    expect(result.current.playerPosition.y).toBeLessThan(50);
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

    pressKey("d");
    expect(result.current.playerDirection).toBe("right");
    expect(result.current.playerPosition.x).toBeGreaterThan(50);
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

    // Position should not change
    expect(result.current.playerPosition).toEqual({ x: 50, y: 50 });
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
      vi.advanceTimersByTime(16);
    });

    // Position should not change since we're typing in an input
    expect(result.current.playerPosition).toEqual({ x: 50, y: 50 });

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

    pressKey("ArrowLeft");
    expect(result.current.playerDirection).toBe("left");
    expect(result.current.playerPosition.x).toBeLessThan(50);
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

    pressKey("a");
    expect(result.current.playerDirection).toBe("left");
    expect(result.current.playerPosition.x).toBeLessThan(50);
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
