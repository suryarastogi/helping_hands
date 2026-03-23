import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { loadPlayerName, savePlayerName, useMultiplayer } from "./useMultiplayer";

// ---------------------------------------------------------------------------
// Yjs / y-websocket mocks
// ---------------------------------------------------------------------------

class MockAwareness {
  private _localState: Record<string, unknown> = {};
  private _states = new Map<number, Record<string, unknown>>();
  private _listeners: Record<string, Array<() => void>> = {};

  getLocalState() { return this._localState; }
  getStates() { return this._states; }

  setLocalStateField(field: string, value: unknown) {
    this._localState[field] = value;
  }

  on(event: string, cb: () => void) {
    (this._listeners[event] ??= []).push(cb);
  }

  off(event: string, cb: () => void) {
    const arr = this._listeners[event];
    if (arr) {
      const idx = arr.indexOf(cb);
      if (idx >= 0) arr.splice(idx, 1);
    }
  }

  _setRemoteStates(states: Map<number, Record<string, unknown>>) {
    this._states = states;
    (this._listeners["change"] ?? []).forEach((cb) => cb());
  }
}

let mockAwareness: MockAwareness;
let mockProviderDestroyCalled: boolean;
let mockDocDestroyCalled: boolean;
const MOCK_CLIENT_ID = 42;

vi.mock("yjs", () => ({
  Doc: class MockDoc {
    clientID = MOCK_CLIENT_ID;
    destroy() { mockDocDestroyCalled = true; }
  },
}));

vi.mock("y-websocket", () => ({
  WebsocketProvider: class MockProvider {
    awareness: MockAwareness;
    _listeners: Record<string, Array<(arg: unknown) => void>> = {};
    constructor() {
      mockAwareness = new MockAwareness();
      this.awareness = mockAwareness;
    }
    on(event: string, cb: (arg: unknown) => void) {
      (this._listeners[event] ??= []).push(cb);
    }
    off(event: string, cb: (arg: unknown) => void) {
      const arr = this._listeners[event];
      if (arr) {
        const idx = arr.indexOf(cb);
        if (idx >= 0) arr.splice(idx, 1);
      }
    }
    destroy() { mockProviderDestroyCalled = true; }
  },
}));

// ---------------------------------------------------------------------------
// loadPlayerName / savePlayerName
// ---------------------------------------------------------------------------

describe("loadPlayerName / savePlayerName", () => {
  beforeEach(() => localStorage.clear());

  it("returns empty string when nothing saved", () => {
    expect(loadPlayerName()).toBe("");
  });

  it("persists and loads a name", () => {
    savePlayerName("Alice");
    expect(loadPlayerName()).toBe("Alice");
  });

  it("overwrites previous name", () => {
    savePlayerName("Alice");
    savePlayerName("Bob");
    expect(loadPlayerName()).toBe("Bob");
  });
});

// ---------------------------------------------------------------------------
// useMultiplayer hook
// ---------------------------------------------------------------------------

describe("useMultiplayer hook", () => {
  const stableWsUrl = (path: string) => `ws://localhost${path}`;
  const defaultOpts = () => ({
    active: true,
    playerPosition: { x: 50, y: 50 },
    playerDirection: "down" as const,
    isPlayerWalking: false,
    wsUrlBuilder: stableWsUrl,
  });

  beforeEach(() => {
    mockProviderDestroyCalled = false;
    mockDocDestroyCalled = false;
  });

  it("manages connection lifecycle and awareness state", () => {
    // Inactive: stays disconnected
    const { result, rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: { ...defaultOpts(), active: false } },
    );
    expect(result.current.connectionStatus).toBe("disconnected");
    expect(result.current.remotePlayers).toEqual([]);

    // Activate: sets awareness with default name
    rerender(defaultOpts());
    const player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.player_id).toBe(String(MOCK_CLIENT_ID));
    expect(player.name).toBe(`Player ${(MOCK_CLIENT_ID % 1000) + 1}`);

    // Deactivate: destroys provider and doc
    rerender({ ...defaultOpts(), active: false });
    expect(mockProviderDestroyCalled).toBe(true);
    expect(mockDocDestroyCalled).toBe(true);
  });

  it("supports custom player name and position updates", () => {
    const { rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: { ...defaultOpts(), playerName: "Zara" } },
    );
    let player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.name).toBe("Zara");

    // Name change does NOT trigger reconnect
    mockProviderDestroyCalled = false;
    rerender({ ...defaultOpts(), playerName: "Bob" });
    player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.name).toBe("Bob");
    expect(mockProviderDestroyCalled).toBe(false);

    // Position update
    rerender({ ...defaultOpts(), playerName: "Bob", playerPosition: { x: 70, y: 80 } });
    player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.x).toBe(70);
    expect(player.y).toBe(80);
  });

  it("tracks remote players and emotes from awareness", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    states.set(100, {
      player: { player_id: "100", name: "HookBob", color: "#e11d48", x: 30, y: 40, direction: "left", walking: true, emote: "wave" },
    });

    act(() => mockAwareness._setRemoteStates(states));

    expect(result.current.remotePlayers).toHaveLength(1);
    expect(result.current.remotePlayers[0].name).toBe("HookBob");
    expect(result.current.remoteEmotes["100"]).toBe("wave");
  });

  it("triggerEmote sets and clears local emote", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    act(() => result.current.triggerEmote("1"));
    expect(result.current.localEmote).toBe("wave");

    // Unknown key does nothing
    act(() => result.current.triggerEmote("9"));
    expect(result.current.localEmote).toBe("wave");

    act(() => vi.advanceTimersByTime(2000));
    expect(result.current.localEmote).toBeNull();

    vi.useRealTimers();
  });

  it("sendChat sets and clears local chat message", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    act(() => result.current.sendChat("Hello!"));
    expect(result.current.localChat).toBe("Hello!");

    // Awareness state should have the chat
    const player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.chat).toBe("Hello!");

    // After CHAT_DISPLAY_MS, chat clears
    act(() => vi.advanceTimersByTime(4000));
    expect(result.current.localChat).toBeNull();

    vi.useRealTimers();
  });

  it("sendChat ignores empty/whitespace messages", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    act(() => result.current.sendChat("   "));
    expect(result.current.localChat).toBeNull();
  });

  it("tracks remote chat messages from awareness", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    states.set(200, {
      player: { player_id: "200", name: "ChatBot", color: "#2563eb", x: 60, y: 60, direction: "right", walking: false, emote: null, chat: "Hi there" },
    });

    act(() => mockAwareness._setRemoteStates(states));

    expect(result.current.remoteChats["200"]).toBe("Hi there");
  });
});
