import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import {
  EMOTE_DISPLAY_MS,
  EMOTE_KEY_BINDINGS,
  EMOTE_MAP,
  PLAYER_COLORS,
  useMultiplayer,
} from "./useMultiplayer";
import { WebsocketProvider as MockedWSProvider } from "y-websocket";

// ---------------------------------------------------------------------------
// Mocks — Yjs + y-websocket
// ---------------------------------------------------------------------------

const mockAwarenessOn = vi.fn();
const mockAwarenessOff = vi.fn();
const mockAwarenessSetLocalStateField = vi.fn();
const mockAwarenessGetLocalState = vi.fn(() => ({
  player: { player_id: "42", name: "Player 43", color: "#e11d48", x: 50, y: 50, direction: "down", walking: false, emote: null },
}));
const mockAwarenessGetStates = vi.fn(() => new Map());

const mockProviderOn = vi.fn();
const mockProviderOff = vi.fn();
const mockProviderDestroy = vi.fn();

/** Tracks the clientID of the most recently created Y.Doc mock. */
let lastDocClientId = 0;

vi.mock("yjs", () => {
  let clientIdCounter = 42;
  return {
    Doc: vi.fn().mockImplementation(() => {
      const id = clientIdCounter++;
      lastDocClientId = id;
      return { clientID: id, destroy: vi.fn() };
    }),
  };
});

vi.mock("y-websocket", () => ({
  WebsocketProvider: vi.fn().mockImplementation(() => ({
    on: mockProviderOn,
    off: mockProviderOff,
    destroy: mockProviderDestroy,
    awareness: {
      on: mockAwarenessOn,
      off: mockAwarenessOff,
      setLocalStateField: mockAwarenessSetLocalStateField,
      getLocalState: mockAwarenessGetLocalState,
      getStates: mockAwarenessGetStates,
    },
  })),
}));

vi.mock("../App", () => ({
  wsUrl: (path: string) => `ws://localhost${path}`,
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const defaultProps = {
  active: false,
  playerPosition: { x: 50, y: 50 },
  playerDirection: "down" as const,
  isPlayerWalking: false,
};

afterEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

describe("PLAYER_COLORS", () => {
  it("has 10 unique hex colours", () => {
    expect(PLAYER_COLORS).toHaveLength(10);
    expect(new Set(PLAYER_COLORS).size).toBe(10);
    for (const c of PLAYER_COLORS) {
      expect(c).toMatch(/^#[0-9a-f]{6}$/);
    }
  });
});

describe("EMOTE_MAP", () => {
  it("maps emote names to emoji strings", () => {
    expect(Object.keys(EMOTE_MAP)).toEqual(["wave", "celebrate", "thumbsup", "sparkle"]);
    for (const v of Object.values(EMOTE_MAP)) {
      expect(typeof v).toBe("string");
      expect(v.length).toBeGreaterThan(0);
    }
  });
});

describe("EMOTE_KEY_BINDINGS", () => {
  it("maps number keys to emote names", () => {
    expect(EMOTE_KEY_BINDINGS["1"]).toBe("wave");
    expect(EMOTE_KEY_BINDINGS["2"]).toBe("celebrate");
    expect(EMOTE_KEY_BINDINGS["3"]).toBe("thumbsup");
    expect(EMOTE_KEY_BINDINGS["4"]).toBe("sparkle");
  });

  it("every binding points to a key in EMOTE_MAP", () => {
    for (const emote of Object.values(EMOTE_KEY_BINDINGS)) {
      expect(EMOTE_MAP).toHaveProperty(emote);
    }
  });
});

describe("EMOTE_DISPLAY_MS", () => {
  it("is 2000ms", () => {
    expect(EMOTE_DISPLAY_MS).toBe(2000);
  });
});

// ---------------------------------------------------------------------------
// Hook behaviour
// ---------------------------------------------------------------------------

describe("useMultiplayer", () => {
  it("returns disconnected state when inactive", () => {
    const { result } = renderHook(() => useMultiplayer(defaultProps));

    expect(result.current.remotePlayers).toEqual([]);
    expect(result.current.remoteEmotes).toEqual({});
    expect(result.current.localEmote).toBeNull();
    expect(result.current.yjsConnStatus).toBe("disconnected");
  });

  it("creates Yjs doc and provider when active", () => {
    const { unmount } = renderHook(() =>
      useMultiplayer({ ...defaultProps, active: true }),
    );

    // Provider should be connected (constructor called).
    expect(MockedWSProvider).toHaveBeenCalledWith(
      "ws://localhost/ws/yjs",
      "hand-world",
      expect.anything(),
    );

    // Awareness state should be initialised.
    expect(mockAwarenessSetLocalStateField).toHaveBeenCalledWith(
      "player",
      expect.objectContaining({
        x: 50,
        y: 50,
        direction: "down",
        walking: false,
        emote: null,
      }),
    );

    // Status listener should be registered.
    expect(mockProviderOn).toHaveBeenCalledWith("status", expect.any(Function));
    expect(mockAwarenessOn).toHaveBeenCalledWith("change", expect.any(Function));

    unmount();
  });

  it("destroys provider on deactivation", () => {
    const { rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: { ...defaultProps, active: true } },
    );

    rerender({ ...defaultProps, active: false });

    expect(mockProviderDestroy).toHaveBeenCalled();
  });

  it("sends position updates via awareness when player moves", () => {
    const { rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: { ...defaultProps, active: true } },
    );

    mockAwarenessSetLocalStateField.mockClear();

    rerender({
      ...defaultProps,
      active: true,
      playerPosition: { x: 60, y: 70 },
      playerDirection: "right" as const,
      isPlayerWalking: true,
    });

    expect(mockAwarenessSetLocalStateField).toHaveBeenCalledWith(
      "player",
      expect.objectContaining({
        x: 60,
        y: 70,
        direction: "right",
        walking: true,
      }),
    );
  });

  it("derives remote players from awareness state changes", () => {
    const remotePeerState = {
      player: {
        player_id: "99",
        name: "Player 100",
        color: "#2563eb",
        x: 30,
        y: 40,
        direction: "left",
        walking: true,
        emote: "wave",
      },
    };

    const { result } = renderHook(() =>
      useMultiplayer({ ...defaultProps, active: true }),
    );

    // Use the actual clientID assigned to this doc instance.
    const localId = lastDocClientId;
    mockAwarenessGetStates.mockReturnValue(
      new Map([
        [localId, { player: { player_id: String(localId), name: "Me", color: "#e11d48", x: 50, y: 50, direction: "down", walking: false, emote: null } }],
        [99, remotePeerState],
      ]),
    );

    // Trigger awareness change callback.
    const changeCallback = mockAwarenessOn.mock.calls.find(
      ([event]: [string]) => event === "change",
    )?.[1];
    expect(changeCallback).toBeDefined();

    act(() => {
      changeCallback();
    });

    expect(result.current.remotePlayers).toHaveLength(1);
    expect(result.current.remotePlayers[0]).toEqual({
      player_id: "99",
      name: "Player 100",
      color: "#2563eb",
      x: 30,
      y: 40,
      direction: "left",
      walking: true,
    });
    expect(result.current.remoteEmotes).toEqual({ "99": "wave" });
  });

  it("broadcasts emotes via keydown and clears after timeout", () => {
    vi.useFakeTimers();

    const { result } = renderHook(() =>
      useMultiplayer({ ...defaultProps, active: true }),
    );

    mockAwarenessSetLocalStateField.mockClear();

    // Press "1" to trigger wave emote.
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "1" }));
    });

    expect(result.current.localEmote).toBe("wave");
    expect(mockAwarenessSetLocalStateField).toHaveBeenCalledWith(
      "player",
      expect.objectContaining({ emote: "wave" }),
    );

    // After EMOTE_DISPLAY_MS, emote should be cleared.
    act(() => {
      vi.advanceTimersByTime(EMOTE_DISPLAY_MS);
    });

    expect(result.current.localEmote).toBeNull();

    vi.useRealTimers();
  });

  it("ignores emote keys when typing in an input", () => {
    renderHook(() =>
      useMultiplayer({ ...defaultProps, active: true }),
    );

    mockAwarenessSetLocalStateField.mockClear();

    const input = document.createElement("input");
    document.body.appendChild(input);
    input.focus();

    act(() => {
      input.dispatchEvent(new KeyboardEvent("keydown", { key: "1", bubbles: true }));
    });

    // No emote broadcast when typing.
    const emoteCalls = mockAwarenessSetLocalStateField.mock.calls.filter(
      ([, state]: [string, Record<string, unknown>]) => state.emote === "wave",
    );
    expect(emoteCalls).toHaveLength(0);

    document.body.removeChild(input);
  });

  it("updates connection status via provider status events", () => {
    const { result } = renderHook(() =>
      useMultiplayer({ ...defaultProps, active: true }),
    );

    const statusCallback = mockProviderOn.mock.calls.find(
      ([event]: [string]) => event === "status",
    )?.[1];
    expect(statusCallback).toBeDefined();

    act(() => {
      statusCallback({ status: "connecting" });
    });
    expect(result.current.yjsConnStatus).toBe("connecting");

    act(() => {
      statusCallback({ status: "connected" });
    });
    expect(result.current.yjsConnStatus).toBe("connected");
  });
});
