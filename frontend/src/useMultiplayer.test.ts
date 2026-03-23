import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// ── Mock yjs + y-websocket ─────────────────────────────────────────────
// vi.mock factories are hoisted, so we must use vi.hoisted() for shared refs.

const {
  mockSetLocalStateField,
  mockGetStates,
  mockAwarenessOn,
  mockAwarenessOff,
  mockDestroy,
  mockProviderOn,
  mockProviderOff,
  mockAwareness,
} = vi.hoisted(() => {
  const mockSetLocalStateField = vi.fn();
  const mockGetStates = vi.fn().mockReturnValue(new Map());
  const mockAwarenessOn = vi.fn();
  const mockAwarenessOff = vi.fn();
  const mockDestroy = vi.fn();
  const mockProviderOn = vi.fn();
  const mockProviderOff = vi.fn();

  const mockAwareness = {
    setLocalStateField: mockSetLocalStateField,
    getStates: mockGetStates,
    clientID: 1,
    on: mockAwarenessOn,
    off: mockAwarenessOff,
  };

  return {
    mockSetLocalStateField,
    mockGetStates,
    mockAwarenessOn,
    mockAwarenessOff,
    mockDestroy,
    mockProviderOn,
    mockProviderOff,
    mockAwareness,
  };
});

vi.mock("yjs", () => ({
  Doc: vi.fn().mockImplementation(() => ({
    destroy: vi.fn(),
  })),
}));

vi.mock("y-websocket", () => ({
  WebsocketProvider: vi.fn().mockImplementation(() => ({
    awareness: mockAwareness,
    on: mockProviderOn,
    off: mockProviderOff,
    destroy: mockDestroy,
  })),
}));

// Now import the hook (after mocks are in place).
import { useMultiplayer } from "./useMultiplayer";
import type { LocalPlayerState, RemotePlayer } from "./useMultiplayer";
import { Doc } from "yjs";
import { WebsocketProvider } from "y-websocket";

// ── Tests ──────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  mockGetStates.mockReturnValue(new Map());
});

describe("useMultiplayer", () => {
  it("does not connect when disabled", () => {
    const { result } = renderHook(() =>
      useMultiplayer({ enabled: false })
    );

    expect(Doc).not.toHaveBeenCalled();
    expect(WebsocketProvider).not.toHaveBeenCalled();
    expect(result.current.remotePlayers).toEqual([]);
    expect(result.current.connected).toBe(false);
    expect(result.current.connectionCount).toBe(0);
  });

  it("connects and sets initial awareness when enabled", () => {
    renderHook(() => useMultiplayer({ enabled: true }));

    expect(Doc).toHaveBeenCalledOnce();
    expect(WebsocketProvider).toHaveBeenCalledOnce();

    // Should set initial player state.
    expect(mockSetLocalStateField).toHaveBeenCalledWith(
      "player",
      expect.objectContaining({
        position: { x: 50, y: 50 },
        direction: "down",
        walking: false,
      })
    );
  });

  it("cleans up on unmount", () => {
    const { unmount } = renderHook(() =>
      useMultiplayer({ enabled: true })
    );

    unmount();
    expect(mockDestroy).toHaveBeenCalled();
    expect(mockAwarenessOff).toHaveBeenCalledWith("change", expect.any(Function));
    expect(mockProviderOff).toHaveBeenCalledWith("status", expect.any(Function));
  });

  it("cleans up when switching from enabled to disabled", () => {
    const { rerender } = renderHook(
      ({ enabled }) => useMultiplayer({ enabled }),
      { initialProps: { enabled: true } }
    );

    rerender({ enabled: false });
    expect(mockDestroy).toHaveBeenCalled();
  });

  it("updateLocalState broadcasts player state", () => {
    const { result } = renderHook(() =>
      useMultiplayer({ enabled: true })
    );

    mockSetLocalStateField.mockClear();

    const state: LocalPlayerState = {
      position: { x: 30, y: 70 },
      direction: "left",
      walking: true,
    };

    act(() => {
      result.current.updateLocalState(state);
    });

    expect(mockSetLocalStateField).toHaveBeenCalledWith(
      "player",
      expect.objectContaining({
        position: { x: 30, y: 70 },
        direction: "left",
        walking: true,
        name: expect.any(String),
        color: expect.any(String),
      })
    );
  });

  it("parses remote players from awareness state changes", () => {
    const { result } = renderHook(() =>
      useMultiplayer({ enabled: true })
    );

    const changeCall = mockAwarenessOn.mock.calls.find(
      (c: unknown[]) => c[0] === "change"
    );
    expect(changeCall).toBeTruthy();
    const onAwarenessChange = changeCall![1];

    const states = new Map();
    states.set(1, {}); // local client
    states.set(42, {
      player: {
        position: { x: 20, y: 80 },
        direction: "right",
        walking: true,
        name: "TestPlayer",
        color: "#ff0000",
      },
    });
    states.set(99, {
      player: {
        position: { x: 60, y: 40 },
        direction: "up",
        walking: false,
        name: "OtherPlayer",
        color: "#00ff00",
      },
    });
    mockGetStates.mockReturnValue(states);

    act(() => {
      onAwarenessChange();
    });

    expect(result.current.remotePlayers).toHaveLength(2);
    expect(result.current.connectionCount).toBe(3);

    const player42 = result.current.remotePlayers.find(
      (p: RemotePlayer) => p.clientId === 42
    );
    expect(player42).toEqual({
      clientId: 42,
      name: "TestPlayer",
      color: "#ff0000",
      position: { x: 20, y: 80 },
      direction: "right",
      walking: true,
    });
  });

  it("ignores awareness entries without player data", () => {
    const { result } = renderHook(() =>
      useMultiplayer({ enabled: true })
    );

    const changeCall = mockAwarenessOn.mock.calls.find(
      (c: unknown[]) => c[0] === "change"
    );
    const onAwarenessChange = changeCall![1];

    const states = new Map();
    states.set(1, {});
    states.set(42, {});
    states.set(99, { player: null });
    mockGetStates.mockReturnValue(states);

    act(() => {
      onAwarenessChange();
    });

    expect(result.current.remotePlayers).toHaveLength(0);
  });

  it("tracks connected status via provider status event", () => {
    const { result } = renderHook(() =>
      useMultiplayer({ enabled: true })
    );

    const statusCall = mockProviderOn.mock.calls.find(
      (c: unknown[]) => c[0] === "status"
    );
    expect(statusCall).toBeTruthy();
    const onStatus = statusCall![1];

    act(() => {
      onStatus({ status: "connected" });
    });
    expect(result.current.connected).toBe(true);

    act(() => {
      onStatus({ status: "disconnected" });
    });
    expect(result.current.connected).toBe(false);
  });

  it("uses custom wsUrl when provided", () => {
    renderHook(() =>
      useMultiplayer({ enabled: true, wsUrl: "ws://custom:9999" })
    );

    expect(WebsocketProvider).toHaveBeenCalledWith(
      "ws://custom:9999",
      "world",
      expect.anything(),
      expect.objectContaining({ connect: true })
    );
  });
});
