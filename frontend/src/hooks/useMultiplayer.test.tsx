import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { loadPlayerColor, loadPlayerName, savePlayerColor, savePlayerName, useMultiplayer } from "./useMultiplayer";

// ---------------------------------------------------------------------------
// Yjs / y-websocket mocks
// ---------------------------------------------------------------------------

type AwarenessChanges = { added: number[]; updated: number[]; removed: number[] };
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AwarenessListener = (changes: AwarenessChanges, ...rest: any[]) => void;

class MockAwareness {
  private _localState: Record<string, unknown> = {};
  private _states = new Map<number, Record<string, unknown>>();
  private _listeners: Record<string, AwarenessListener[]> = {};
  private _prevClientIds = new Set<number>();

  getLocalState() { return this._localState; }
  getStates() { return this._states; }

  setLocalStateField(field: string, value: unknown) {
    this._localState[field] = value;
  }

  on(event: string, cb: AwarenessListener) {
    (this._listeners[event] ??= []).push(cb);
  }

  off(event: string, cb: AwarenessListener) {
    const arr = this._listeners[event];
    if (arr) {
      const idx = arr.indexOf(cb);
      if (idx >= 0) arr.splice(idx, 1);
    }
  }

  _setRemoteStates(states: Map<number, Record<string, unknown>>) {
    const newIds = new Set(states.keys());
    const added: number[] = [];
    const removed: number[] = [];
    const updated: number[] = [];
    for (const id of newIds) {
      if (!this._prevClientIds.has(id)) added.push(id);
      else updated.push(id);
    }
    for (const id of this._prevClientIds) {
      if (!newIds.has(id)) removed.push(id);
    }
    this._states = states;
    this._prevClientIds = newIds;
    const changes: AwarenessChanges = { added, updated, removed };
    (this._listeners["change"] ?? []).forEach((cb) => cb(changes));
  }
}

class MockYMap {
  private _data = new Map<string, unknown>();
  private _observers: Array<() => void> = [];

  get size() { return this._data.size; }
  get(key: string) { return this._data.get(key); }
  set(key: string, value: unknown) {
    this._data.set(key, value);
    this._observers.forEach((cb) => cb());
  }
  delete(key: string) {
    this._data.delete(key);
    this._observers.forEach((cb) => cb());
  }
  keys() { return this._data.keys(); }
  forEach(cb: (value: unknown, key: string) => void) { this._data.forEach(cb); }
  observe(cb: () => void) { this._observers.push(cb); }
  unobserve(cb: () => void) {
    const idx = this._observers.indexOf(cb);
    if (idx >= 0) this._observers.splice(idx, 1);
  }
}

let mockAwareness: MockAwareness;
let mockProviderDestroyCalled: boolean;
let mockProviderDisconnectCalled: boolean;
let mockDocDestroyCalled: boolean;
let latestMockProvider: { _listeners: Record<string, Array<(arg: unknown) => void>> } | null = null;
const MOCK_CLIENT_ID = 42;

vi.mock("yjs", () => ({
  Doc: class MockDoc {
    clientID = MOCK_CLIENT_ID;
    private _maps = new Map<string, MockYMap>();
    getMap(name: string) {
      if (!this._maps.has(name)) {
        this._maps.set(name, new MockYMap());
      }
      return this._maps.get(name)!;
    }
    transact(fn: () => void) { fn(); }
    destroy() { mockDocDestroyCalled = true; }
  },
}));

vi.mock("y-websocket", () => {
  function MockProvider() {
    mockAwareness = new MockAwareness();
    const instance = {
      awareness: mockAwareness,
      _listeners: {} as Record<string, Array<(arg: unknown) => void>>,
      on(event: string, cb: (arg: unknown) => void) {
        (instance._listeners[event] ??= []).push(cb);
      },
      off(event: string, cb: (arg: unknown) => void) {
        const arr = instance._listeners[event];
        if (arr) {
          const idx = arr.indexOf(cb);
          if (idx >= 0) arr.splice(idx, 1);
        }
      },
      disconnect() { mockProviderDisconnectCalled = true; },
      destroy() { mockProviderDestroyCalled = true; },
    };
    latestMockProvider = instance;
    return instance;
  }
  return { WebsocketProvider: MockProvider };
});

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

  it("loadPlayerName returns empty string when localStorage throws", () => {
    const spy = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("SecurityError");
    });
    expect(loadPlayerName()).toBe("");
    spy.mockRestore();
  });

  it("savePlayerName silently ignores storage errors", () => {
    const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("QuotaExceededError");
    });
    expect(() => savePlayerName("Alice")).not.toThrow();
    spy.mockRestore();
  });
});

// ---------------------------------------------------------------------------
// loadPlayerColor / savePlayerColor
// ---------------------------------------------------------------------------

describe("loadPlayerColor / savePlayerColor", () => {
  beforeEach(() => localStorage.clear());

  it("returns empty string when nothing saved", () => {
    expect(loadPlayerColor()).toBe("");
  });

  it("persists and loads a color", () => {
    savePlayerColor("#e11d48");
    expect(loadPlayerColor()).toBe("#e11d48");
  });

  it("loadPlayerColor returns empty string when localStorage throws", () => {
    const spy = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("SecurityError");
    });
    expect(loadPlayerColor()).toBe("");
    spy.mockRestore();
  });

  it("savePlayerColor silently ignores storage errors", () => {
    const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("QuotaExceededError");
    });
    expect(() => savePlayerColor("#e11d48")).not.toThrow();
    spy.mockRestore();
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
    mockProviderDisconnectCalled = false;
    mockDocDestroyCalled = false;
    latestMockProvider = null;
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
    vi.useFakeTimers();
    const stablePos = { x: 50, y: 50 };
    const baseOpts = { ...defaultOpts(), playerPosition: stablePos };
    const { rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: { ...baseOpts, playerName: "Zara" } },
    );
    let player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.name).toBe("Zara");

    // Name change does NOT trigger reconnect
    mockProviderDestroyCalled = false;
    rerender({ ...baseOpts, playerName: "Bob" });
    player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.name).toBe("Bob");
    expect(mockProviderDestroyCalled).toBe(false);

    // Advance past throttle window so position update broadcasts immediately.
    act(() => vi.advanceTimersByTime(70));

    // Position update
    rerender({ ...baseOpts, playerName: "Bob", playerPosition: { x: 70, y: 80 } });
    player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.x).toBe(70);
    expect(player.y).toBe(80);

    vi.useRealTimers();
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

  // --- Chat history ---

  it("accumulates local chat messages in chatHistory", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    act(() => result.current.sendChat("First"));
    expect(result.current.chatHistory).toHaveLength(1);
    expect(result.current.chatHistory[0].text).toBe("First");
    expect(result.current.chatHistory[0].playerName).toBeTruthy();

    act(() => vi.advanceTimersByTime(5000));

    act(() => result.current.sendChat("Second"));
    expect(result.current.chatHistory).toHaveLength(2);
    expect(result.current.chatHistory[1].text).toBe("Second");

    vi.useRealTimers();
  });

  it("accumulates remote chat messages in chatHistory", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    states.set(300, {
      player: { player_id: "300", name: "RemoteUser", color: "#16a34a", x: 50, y: 50, direction: "down", walking: false, emote: null, chat: "Hey!" },
    });

    act(() => mockAwareness._setRemoteStates(states));

    // 1 system join message + 1 chat message
    expect(result.current.chatHistory).toHaveLength(2);
    expect(result.current.chatHistory[0].isSystem).toBe(true);
    expect(result.current.chatHistory[1].text).toBe("Hey!");
    expect(result.current.chatHistory[1].playerName).toBe("RemoteUser");
    expect(result.current.chatHistory[1].playerColor).toBe("#16a34a");
  });

  it("deduplicates repeated remote chat awareness updates", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    states.set(400, {
      player: { player_id: "400", name: "Dup", color: "#d97706", x: 50, y: 50, direction: "down", walking: false, emote: null, chat: "Repeat" },
    });

    act(() => mockAwareness._setRemoteStates(states));
    act(() => mockAwareness._setRemoteStates(states));

    // 1 system join + 1 chat (second awareness update is deduped)
    expect(result.current.chatHistory).toHaveLength(2);
    expect(result.current.chatHistory[0].isSystem).toBe(true);
    expect(result.current.chatHistory[1].text).toBe("Repeat");
  });

  it("clears chatHistory when deactivated", () => {
    const { result, rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    act(() => result.current.sendChat("Before deactivate"));
    expect(result.current.chatHistory).toHaveLength(1);

    rerender({ ...defaultOpts(), active: false });
    expect(result.current.chatHistory).toHaveLength(0);
  });

  // --- Idle detection ---

  it("starts as not idle", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));
    expect(result.current.isLocalIdle).toBe(false);
  });

  it("becomes idle after IDLE_TIMEOUT_MS of inactivity", () => {
    vi.useFakeTimers();

    // Use stable object references so position effect doesn't re-run on re-render.
    const stablePos = { x: 50, y: 50 };
    const opts = { ...defaultOpts(), playerPosition: stablePos };
    const { result } = renderHook(() => useMultiplayer(opts));
    expect(result.current.isLocalIdle).toBe(false);

    // Advance past the idle timeout (30s) + one check interval (5s).
    act(() => vi.advanceTimersByTime(35_000));

    expect(result.current.isLocalIdle).toBe(true);

    vi.useRealTimers();
  });

  it("resets idle state on position change", () => {
    vi.useFakeTimers();
    const stablePos = { x: 50, y: 50 };
    const opts = { ...defaultOpts(), playerPosition: stablePos };
    const { result, rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: opts },
    );

    // Go idle
    act(() => vi.advanceTimersByTime(35_000));
    expect(result.current.isLocalIdle).toBe(true);

    // Move — should reset idle
    const newPos = { x: 60, y: 70 };
    rerender({ ...opts, playerPosition: newPos });
    expect(result.current.isLocalIdle).toBe(false);

    vi.useRealTimers();
  });

  it("tracks idle state of remote players from awareness", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    states.set(500, {
      player: { player_id: "500", name: "IdlePlayer", color: "#7c3aed", x: 50, y: 50, direction: "down", walking: false, idle: true, emote: null, chat: null },
    });

    act(() => mockAwareness._setRemoteStates(states));

    expect(result.current.remotePlayers).toHaveLength(1);
    expect(result.current.remotePlayers[0].idle).toBe(true);
  });

  it("cleans up dedupe keys when remote chat clears", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    // Remote sends a chat
    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    states.set(600, {
      player: { player_id: "600", name: "ChatterBox", color: "#d97706", x: 50, y: 50, direction: "down", walking: false, emote: null, chat: "First msg" },
    });
    act(() => mockAwareness._setRemoteStates(states));
    // 1 system join + 1 chat
    expect(result.current.chatHistory).toHaveLength(2);

    // Remote clears their chat (chat becomes null)
    const clearedStates = new Map<number, Record<string, unknown>>();
    clearedStates.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    clearedStates.set(600, {
      player: { player_id: "600", name: "ChatterBox", color: "#d97706", x: 50, y: 50, direction: "down", walking: false, emote: null, chat: null },
    });
    act(() => mockAwareness._setRemoteStates(clearedStates));

    // Now remote sends a new message — should NOT be deduped since key was cleaned
    const newStates = new Map<number, Record<string, unknown>>();
    newStates.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    newStates.set(600, {
      player: { player_id: "600", name: "ChatterBox", color: "#d97706", x: 50, y: 50, direction: "down", walking: false, emote: null, chat: "Second msg" },
    });
    act(() => mockAwareness._setRemoteStates(newStates));
    // 1 system join + 2 chat messages
    expect(result.current.chatHistory).toHaveLength(3);
    expect(result.current.chatHistory[2].text).toBe("Second msg");
  });

  it("falls back to defaults for remote players with missing fields", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    // Remote player with minimal fields — triggers all ?? fallbacks
    states.set(700, {
      player: { x: 10, y: 20 },
    });
    act(() => mockAwareness._setRemoteStates(states));

    expect(result.current.remotePlayers).toHaveLength(1);
    const rp = result.current.remotePlayers[0];
    expect(rp.player_id).toBe(String(700));
    expect(rp.name).toBe(`Player ${(700 % 1000) + 1}`);
    expect(rp.direction).toBe("down");
    expect(rp.walking).toBe(false);
    expect(rp.idle).toBe(false);
  });

  it("skips awareness entries without player field", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    // Client with no player field at all
    states.set(800, { cursor: { x: 10, y: 10 } });
    act(() => mockAwareness._setRemoteStates(states));

    expect(result.current.remotePlayers).toHaveLength(0);
  });

  it("emote key bindings only fire when world is active", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: { ...defaultOpts(), active: false } },
    );

    // Press emote key while inactive — should not trigger
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "1", bubbles: true }));
    });
    expect(result.current.localEmote).toBeNull();

    // Activate and press emote key
    rerender(defaultOpts());
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "1", bubbles: true }));
    });
    expect(result.current.localEmote).toBe("wave");

    act(() => vi.advanceTimersByTime(2000));
    vi.useRealTimers();
  });

  it("emote key bindings ignore input fields", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    // Simulate emote key from within an input
    const input = document.createElement("input");
    document.body.appendChild(input);
    act(() => {
      input.dispatchEvent(new KeyboardEvent("keydown", { key: "1", bubbles: true }));
    });
    expect(result.current.localEmote).toBeNull();
    document.body.removeChild(input);
  });

  // --- Chat cooldown ---

  it("starts with chatOnCooldown as false", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));
    expect(result.current.chatOnCooldown).toBe(false);
  });

  it("sets chatOnCooldown after sending a message", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    act(() => result.current.sendChat("Hello!"));
    expect(result.current.chatOnCooldown).toBe(true);
    expect(result.current.localChat).toBe("Hello!");

    // After cooldown period, should reset
    act(() => vi.advanceTimersByTime(2000));
    expect(result.current.chatOnCooldown).toBe(false);

    vi.useRealTimers();
  });

  it("blocks chat messages during cooldown", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    act(() => result.current.sendChat("First"));
    expect(result.current.localChat).toBe("First");
    expect(result.current.chatHistory).toHaveLength(1);

    // Try to send during cooldown — should be ignored
    act(() => result.current.sendChat("Second"));
    expect(result.current.chatHistory).toHaveLength(1);

    // After cooldown expires, can send again
    act(() => vi.advanceTimersByTime(2000));
    // Also advance past CHAT_DISPLAY_MS to clear the first message
    act(() => vi.advanceTimersByTime(2000));

    act(() => result.current.sendChat("Third"));
    expect(result.current.localChat).toBe("Third");
    expect(result.current.chatHistory).toHaveLength(2);

    vi.useRealTimers();
  });

  // --- Typing state ---

  it("setTyping updates local typing state and broadcasts via awareness", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    expect(result.current.isLocalTyping).toBe(false);

    act(() => result.current.setTyping(true));
    expect(result.current.isLocalTyping).toBe(true);

    // Awareness should reflect typing=true
    const player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.typing).toBe(true);

    act(() => result.current.setTyping(false));
    expect(result.current.isLocalTyping).toBe(false);

    const playerAfter = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(playerAfter.typing).toBe(false);
  });

  it("tracks remote typing state from awareness", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    states.set(900, {
      player: { player_id: "900", name: "Typer", color: "#7c3aed", x: 50, y: 50, direction: "down", walking: false, idle: false, typing: true, emote: null, chat: null },
    });

    act(() => mockAwareness._setRemoteStates(states));

    expect(result.current.remoteTyping["900"]).toBe(true);
    expect(result.current.remotePlayers[0].typing).toBe(true);
  });

  it("clears idle state when deactivated", () => {
    vi.useFakeTimers();
    const stablePos = { x: 50, y: 50 };
    const opts = { ...defaultOpts(), playerPosition: stablePos };
    const { result, rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: opts },
    );

    act(() => vi.advanceTimersByTime(35_000));
    expect(result.current.isLocalIdle).toBe(true);

    rerender({ ...opts, active: false });
    expect(result.current.isLocalIdle).toBe(false);

    vi.useRealTimers();
  });

  // --- Shared decorations (Y.Map) ---

  it("starts with empty decorations", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));
    expect(result.current.decorations).toEqual([]);
  });

  it("placeDecoration adds a decoration to Y.Map and state", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    act(() => result.current.placeDecoration("\u{1F338}", 30, 40));

    expect(result.current.decorations).toHaveLength(1);
    expect(result.current.decorations[0].emoji).toBe("\u{1F338}");
    expect(result.current.decorations[0].x).toBe(30);
    expect(result.current.decorations[0].y).toBe(40);
    expect(result.current.decorations[0].placedBy).toBeTruthy();
  });

  it("clearDecorations removes all decorations", () => {
    vi.useFakeTimers({ now: 1000 });
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    act(() => result.current.placeDecoration("\u{2B50}", 10, 20));
    vi.advanceTimersByTime(1);
    act(() => result.current.placeDecoration("\u{1F525}", 50, 60));
    expect(result.current.decorations).toHaveLength(2);

    act(() => result.current.clearDecorations());
    expect(result.current.decorations).toHaveLength(0);
    vi.useRealTimers();
  });

  it("respects MAX_DECORATIONS limit", () => {
    vi.useFakeTimers({ now: 1000 });
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    // Fill up to max
    for (let i = 0; i < 20; i++) {
      act(() => result.current.placeDecoration("\u{1F338}", i * 4, 50));
      vi.advanceTimersByTime(1);
    }
    expect(result.current.decorations).toHaveLength(20);

    // 21st should be rejected
    act(() => result.current.placeDecoration("\u{2B50}", 90, 90));
    expect(result.current.decorations).toHaveLength(20);
    vi.useRealTimers();
  });

  it("clears decorations when deactivated", () => {
    const { result, rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    act(() => result.current.placeDecoration("\u{1F338}", 50, 50));
    expect(result.current.decorations).toHaveLength(1);

    rerender({ ...defaultOpts(), active: false });
    expect(result.current.decorations).toHaveLength(0);
  });

  it("placeDecoration is no-op when inactive", () => {
    const { result } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: { ...defaultOpts(), active: false } },
    );

    act(() => result.current.placeDecoration("\u{1F338}", 50, 50));
    expect(result.current.decorations).toHaveLength(0);
  });

  // --- Join/leave notifications ---

  it("adds a system message when a remote player joins", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    // First awareness update with a new remote player
    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    states.set(150, {
      player: { player_id: "150", name: "Newcomer", color: "#e11d48", x: 50, y: 50, direction: "down", walking: false },
    });

    act(() => mockAwareness._setRemoteStates(states));

    // Should have a system join message
    const joinMsg = result.current.chatHistory.find((m) => m.isSystem && m.text.includes("joined"));
    expect(joinMsg).toBeDefined();
    expect(joinMsg!.text).toBe("Newcomer joined");
    expect(joinMsg!.isSystem).toBe(true);
  });

  it("adds a system message when a remote player leaves", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    // Add a remote player
    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    states.set(160, {
      player: { player_id: "160", name: "Leaver", color: "#2563eb", x: 50, y: 50, direction: "down", walking: false },
    });
    act(() => mockAwareness._setRemoteStates(states));

    // Remove the remote player
    const statesAfter = new Map<number, Record<string, unknown>>();
    statesAfter.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    act(() => mockAwareness._setRemoteStates(statesAfter));

    const leaveMsg = result.current.chatHistory.find((m) => m.isSystem && m.text.includes("left"));
    expect(leaveMsg).toBeDefined();
    expect(leaveMsg!.text).toContain("left");
    expect(leaveMsg!.isSystem).toBe(true);
  });

  // --- Position throttling ---

  it("throttles position broadcasts to POSITION_BROADCAST_INTERVAL_MS", () => {
    vi.useFakeTimers();
    const { rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    // Initial render broadcasts at x=50. Wait past throttle window.
    act(() => vi.advanceTimersByTime(70));

    // First explicit update broadcasts immediately (window elapsed).
    rerender({ ...defaultOpts(), playerPosition: { x: 55, y: 55 } });
    let player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.x).toBe(55);

    // Rapid second update within throttle window — should NOT broadcast yet.
    rerender({ ...defaultOpts(), playerPosition: { x: 60, y: 60 } });
    player = mockAwareness.getLocalState().player as Record<string, unknown>;
    // Still at 55 because throttle hasn't fired yet
    expect(player.x).toBe(55);

    // Advance past the throttle interval — trailing update fires.
    act(() => vi.advanceTimersByTime(70));
    player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.x).toBe(60);

    vi.useRealTimers();
  });

  it("broadcasts immediately after throttle window passes", () => {
    vi.useFakeTimers();
    const { rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    // Initial render broadcasts x=50. Advance past two throttle windows
    // so the next position update will broadcast immediately.
    act(() => vi.advanceTimersByTime(150));

    // Update should go through immediately since window has long passed.
    rerender({ ...defaultOpts(), playerPosition: { x: 70, y: 70 } });
    const player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.x).toBe(70);

    vi.useRealTimers();
  });

  it("supports custom player color and broadcasts changes without reconnecting", () => {
    const { rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: { ...defaultOpts(), playerColor: "#2563eb" } },
    );
    let player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.color).toBe("#2563eb");

    // Color change does NOT trigger reconnect
    mockProviderDestroyCalled = false;
    rerender({ ...defaultOpts(), playerColor: "#16a34a" });
    player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.color).toBe("#16a34a");
    expect(mockProviderDestroyCalled).toBe(false);
  });

  it("does not add join/leave messages for the local client", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    // Simulate awareness update with only the local client
    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    act(() => mockAwareness._setRemoteStates(states));

    const systemMsgs = result.current.chatHistory.filter((m) => m.isSystem);
    expect(systemMsgs).toHaveLength(0);
  });

  // --- Leave message name resolution ---

  it("uses cached player name in leave messages instead of generic fallback", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    // Add a remote player with a custom name
    const states = new Map<number, Record<string, unknown>>();
    states.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    states.set(170, {
      player: { player_id: "170", name: "CachedAlice", color: "#e11d48", x: 50, y: 50, direction: "down", walking: false },
    });
    act(() => mockAwareness._setRemoteStates(states));

    // Remove the remote player — state is already gone by the time `removed` fires
    const statesAfter = new Map<number, Record<string, unknown>>();
    statesAfter.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    act(() => mockAwareness._setRemoteStates(statesAfter));

    // The leave message should use the cached name, not "Player 171"
    const leaveMsg = result.current.chatHistory.find((m) => m.isSystem && m.text.includes("left"));
    expect(leaveMsg).toBeDefined();
    expect(leaveMsg!.text).toBe("CachedAlice left");
    expect(leaveMsg!.playerColor).toBe("#e11d48");
  });

  // --- Chat dedup allows repeated messages ---

  it("records the same message text sent again after the first bubble expires", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    // Remote sends "Hello"
    const states1 = new Map<number, Record<string, unknown>>();
    states1.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    states1.set(180, {
      player: { player_id: "180", name: "Repeater", color: "#d97706", x: 50, y: 50, direction: "down", walking: false, emote: null, chat: "Hello" },
    });
    act(() => mockAwareness._setRemoteStates(states1));
    // 1 join + 1 chat
    expect(result.current.chatHistory).toHaveLength(2);

    // Remote chat clears (bubble expires)
    const statesCleared = new Map<number, Record<string, unknown>>();
    statesCleared.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    statesCleared.set(180, {
      player: { player_id: "180", name: "Repeater", color: "#d97706", x: 50, y: 50, direction: "down", walking: false, emote: null, chat: null },
    });
    act(() => mockAwareness._setRemoteStates(statesCleared));

    // Remote sends "Hello" again — should NOT be dropped by dedup
    const states2 = new Map<number, Record<string, unknown>>();
    states2.set(MOCK_CLIENT_ID, mockAwareness.getLocalState());
    states2.set(180, {
      player: { player_id: "180", name: "Repeater", color: "#d97706", x: 50, y: 50, direction: "down", walking: false, emote: null, chat: "Hello" },
    });
    act(() => mockAwareness._setRemoteStates(states2));

    // 1 join + 2 chat messages (same text, but second is a new send)
    expect(result.current.chatHistory).toHaveLength(3);
    expect(result.current.chatHistory[1].text).toBe("Hello");
    expect(result.current.chatHistory[2].text).toBe("Hello");
  });

  // --- Reconnection resilience ---

  it("resets reconnectAttempts on successful connection", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    // Simulate disconnect then connect
    const provider = latestMockProvider!;
    act(() => {
      (provider._listeners["status"] ?? []).forEach((cb) => cb({ status: "disconnected" }));
    });
    expect(result.current.reconnectAttempts).toBe(1);

    act(() => {
      (provider._listeners["status"] ?? []).forEach((cb) => cb({ status: "connected" }));
    });
    expect(result.current.reconnectAttempts).toBe(0);
    expect(result.current.connectionStatus).toBe("connected");
  });

  it("increments reconnectAttempts on each disconnect", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));
    const provider = latestMockProvider!;

    act(() => {
      (provider._listeners["status"] ?? []).forEach((cb) => cb({ status: "disconnected" }));
    });
    expect(result.current.reconnectAttempts).toBe(1);

    act(() => {
      (provider._listeners["status"] ?? []).forEach((cb) => cb({ status: "disconnected" }));
    });
    expect(result.current.reconnectAttempts).toBe(2);
  });

  it("transitions to 'failed' status after MAX_RECONNECT_ATTEMPTS disconnects", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));
    const provider = latestMockProvider!;

    // Simulate MAX_RECONNECT_ATTEMPTS disconnects (10)
    for (let i = 0; i < 10; i++) {
      act(() => {
        (provider._listeners["status"] ?? []).forEach((cb) => cb({ status: "disconnected" }));
      });
    }

    expect(result.current.connectionStatus).toBe("failed");
    expect(mockProviderDisconnectCalled).toBe(true);
  });

  it("shows 'connecting' status during reconnection attempts below threshold", () => {
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));
    const provider = latestMockProvider!;

    act(() => {
      (provider._listeners["status"] ?? []).forEach((cb) => cb({ status: "disconnected" }));
    });
    expect(result.current.connectionStatus).toBe("connecting");
    expect(result.current.reconnectAttempts).toBe(1);
  });

  it("resets reconnectAttempts when deactivated", () => {
    const { result, rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );
    const provider = latestMockProvider!;

    // Trigger a disconnect to bump attempts
    act(() => {
      (provider._listeners["status"] ?? []).forEach((cb) => cb({ status: "disconnected" }));
    });
    expect(result.current.reconnectAttempts).toBe(1);

    // Deactivate
    rerender({ ...defaultOpts(), active: false });
    expect(result.current.reconnectAttempts).toBe(0);
    expect(result.current.connectionStatus).toBe("disconnected");
  });

  // -------------------------------------------------------------------------
  // Remote cursor tracking
  // -------------------------------------------------------------------------

  it("extracts remote cursors from awareness state", () => {
    const { result } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    // Simulate a remote player with a cursor position
    const remoteStates = new Map<number, Record<string, unknown>>();
    remoteStates.set(99, {
      player: {
        player_id: "99",
        name: "Alice",
        color: "#e11d48",
        x: 30,
        y: 40,
        direction: "down",
        walking: false,
        idle: false,
        typing: false,
        cursor: { x: 60, y: 70 },
      },
    });

    act(() => {
      mockAwareness._setRemoteStates(remoteStates);
    });

    expect(result.current.remoteCursors).toEqual([
      { player_id: "99", name: "Alice", color: "#e11d48", x: 60, y: 70 },
    ]);
  });

  it("omits cursors when cursor field is null", () => {
    const { result } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    const remoteStates = new Map<number, Record<string, unknown>>();
    remoteStates.set(99, {
      player: {
        player_id: "99",
        name: "Alice",
        color: "#e11d48",
        x: 30,
        y: 40,
        direction: "down",
        walking: false,
        idle: false,
        typing: false,
        cursor: null,
      },
    });

    act(() => {
      mockAwareness._setRemoteStates(remoteStates);
    });

    expect(result.current.remoteCursors).toEqual([]);
  });

  it("updateCursor broadcasts cursor position via awareness", () => {
    vi.useFakeTimers();
    const { result } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    act(() => {
      result.current.updateCursor({ x: 25, y: 75 });
    });

    const player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.cursor).toEqual({ x: 25, y: 75 });

    // Sending null clears the cursor
    act(() => {
      result.current.updateCursor(null);
    });

    const player2 = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player2.cursor).toBeNull();

    vi.useRealTimers();
  });

  it("throttles rapid cursor broadcasts to CURSOR_BROADCAST_INTERVAL_MS", () => {
    vi.useFakeTimers();
    const { result } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    // First cursor update broadcasts immediately (no prior broadcast).
    act(() => result.current.updateCursor({ x: 10, y: 20 }));
    let player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.cursor).toEqual({ x: 10, y: 20 });

    // Rapid second update within throttle window — should NOT broadcast yet.
    act(() => result.current.updateCursor({ x: 30, y: 40 }));
    player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.cursor).toEqual({ x: 10, y: 20 }); // still at first position

    // Advance past the throttle interval — trailing update fires.
    act(() => vi.advanceTimersByTime(110));
    player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.cursor).toEqual({ x: 30, y: 40 });

    vi.useRealTimers();
  });

  it("broadcasts cursor immediately after throttle window passes", () => {
    vi.useFakeTimers();
    const { result } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    // First broadcast
    act(() => result.current.updateCursor({ x: 10, y: 20 }));

    // Wait well past the throttle window
    act(() => vi.advanceTimersByTime(200));

    // Next update should broadcast immediately since window has passed
    act(() => result.current.updateCursor({ x: 50, y: 60 }));
    const player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.cursor).toEqual({ x: 50, y: 60 });

    vi.useRealTimers();
  });

  it("updateCursor(null) cancels pending throttle timer and broadcasts immediately", () => {
    vi.useFakeTimers();
    const { result } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    // First broadcast to set the baseline
    act(() => result.current.updateCursor({ x: 10, y: 20 }));

    // Rapid second update — schedules a trailing broadcast
    act(() => result.current.updateCursor({ x: 30, y: 40 }));
    let player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.cursor).toEqual({ x: 10, y: 20 }); // still throttled

    // Mouse leaves scene — null should cancel the pending timer and broadcast immediately
    act(() => result.current.updateCursor(null));
    player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.cursor).toBeNull();

    // Advance past the interval — no stale trailing broadcast should fire
    act(() => vi.advanceTimersByTime(110));
    player = mockAwareness.getLocalState().player as Record<string, unknown>;
    expect(player.cursor).toBeNull(); // still null, not { x: 30, y: 40 }

    vi.useRealTimers();
  });

  it("clearDecorations is no-op when inactive (doc is null)", () => {
    const { result } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: { ...defaultOpts(), active: false } },
    );

    // Should not throw when doc is null
    expect(() => act(() => result.current.clearDecorations())).not.toThrow();
    expect(result.current.decorations).toHaveLength(0);
  });

  it("updateCursor clamps out-of-range coordinates to [0, 100]", () => {
    vi.useFakeTimers();
    const { result } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    act(() => result.current.updateCursor({ x: -10, y: 150 }));

    const player = mockAwareness.getLocalState().player as Record<string, unknown>;
    const cursor = player.cursor as { x: number; y: number };
    expect(cursor.x).toBe(0);
    expect(cursor.y).toBe(100);

    vi.useRealTimers();
  });

  it("omits cursors when cursor field has non-numeric coordinates", () => {
    const { result } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    const remoteStates = new Map<number, Record<string, unknown>>();
    remoteStates.set(99, {
      player: {
        player_id: "99",
        name: "Alice",
        color: "#e11d48",
        x: 30,
        y: 40,
        direction: "down",
        walking: false,
        cursor: { x: "not-a-number", y: undefined },
      },
    });

    act(() => {
      mockAwareness._setRemoteStates(remoteStates);
    });

    // Non-numeric cursor coords should be filtered out
    expect(result.current.remoteCursors).toEqual([]);
  });

  it("clears remoteCursors when deactivated", () => {
    const { result, rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    // Add a remote cursor
    const remoteStates = new Map<number, Record<string, unknown>>();
    remoteStates.set(99, {
      player: {
        player_id: "99",
        name: "Alice",
        color: "#e11d48",
        x: 30,
        y: 40,
        direction: "down",
        walking: false,
        cursor: { x: 60, y: 70 },
      },
    });
    act(() => {
      mockAwareness._setRemoteStates(remoteStates);
    });
    expect(result.current.remoteCursors.length).toBe(1);

    // Deactivate
    rerender({ ...defaultOpts(), active: false });
    expect(result.current.remoteCursors).toEqual([]);
  });

  // -------------------------------------------------------------------------
  // Timer cleanup on deactivation
  // -------------------------------------------------------------------------

  it("clears emote timer on deactivation — timer does not fire after cleanup", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    // Trigger emote — starts timeouts that would clear localEmote
    act(() => result.current.triggerEmote("1"));
    expect(result.current.localEmote).toBe("wave");

    // Deactivate before the timer fires — cleanup should cancel emote timers.
    // The provider and awareness are destroyed here.
    rerender({ ...defaultOpts(), active: false });

    // Advance past EMOTE_DISPLAY_MS. If the timer wasn't cancelled it would
    // call setLocalStateField on the destroyed provider — this should not
    // throw. The emote display timer was also cancelled.
    act(() => vi.advanceTimersByTime(3000));

    // localEmote still has its value (React state is independent of timers),
    // but the provider-side timer was cancelled so no awareness update fires.
    expect(result.current.localEmote).toBe("wave");

    vi.useRealTimers();
  });

  it("clears chat timers on deactivation — timers do not fire after cleanup", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(
      (props) => useMultiplayer(props),
      { initialProps: defaultOpts() },
    );

    // Send chat — starts cooldown + display + awareness timers
    act(() => result.current.sendChat("Hello!"));
    expect(result.current.localChat).toBe("Hello!");
    expect(result.current.chatOnCooldown).toBe(true);

    // Deactivate before timers fire — cleanup should cancel all chat timers
    rerender({ ...defaultOpts(), active: false });

    // Advance past both CHAT_DISPLAY_MS and CHAT_COOLDOWN_MS.
    // Cancelled timers should not fire on destroyed provider.
    act(() => vi.advanceTimersByTime(5000));

    // React state persists (chat/cooldown) but awareness timers are cancelled.
    expect(result.current.localChat).toBe("Hello!");
    expect(result.current.chatOnCooldown).toBe(true);

    vi.useRealTimers();
  });

  it("rapid emote triggers cancel previous emote timer", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useMultiplayer(defaultOpts()));

    act(() => result.current.triggerEmote("1"));
    expect(result.current.localEmote).toBe("wave");

    // Advance partway through
    act(() => vi.advanceTimersByTime(1000));

    // Trigger again — should cancel previous timer
    act(() => result.current.triggerEmote("2"));
    expect(result.current.localEmote).toBe("celebrate");

    // Original timer at 2000ms should NOT have fired (was cancelled)
    act(() => vi.advanceTimersByTime(1000));
    expect(result.current.localEmote).toBe("celebrate");

    // New timer fires at 2000ms from second trigger
    act(() => vi.advanceTimersByTime(1000));
    expect(result.current.localEmote).toBeNull();

    vi.useRealTimers();
  });
});
