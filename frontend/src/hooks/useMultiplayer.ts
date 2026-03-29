/**
 * useMultiplayer — Yjs awareness-based multiplayer hook for Hand World.
 *
 * Encapsulates Yjs document lifecycle, WebSocket provider connection,
 * awareness-based position/emote broadcasting, and remote player tracking.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";

import {
  CHAT_COOLDOWN_MS,
  CHAT_DISPLAY_MS,
  CHAT_HISTORY_MAX,
  CURSOR_BROADCAST_INTERVAL_MS,
  DECO_COOLDOWN_MS,
  EMOTE_DISPLAY_MS,
  EMOTE_KEY_BINDINGS,
  IDLE_TIMEOUT_MS,
  MAX_DECORATIONS,
  MAX_RECONNECT_ATTEMPTS,
  PLAYER_COLORS,
  POSITION_BROADCAST_INTERVAL_MS,
} from "../constants";
import type { ChatMessage, CursorPosition, PlayerDirection, WorldDecoration } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "failed";

export type RemotePlayer = {
  player_id: string;
  name: string;
  color: string;
  x: number;
  y: number;
  direction: PlayerDirection;
  walking: boolean;
  idle: boolean;
  typing: boolean;
};

export type UseMultiplayerOptions = {
  /** Whether the world view is active — hook only connects when true. */
  active: boolean;
  /** Current local player position. */
  playerPosition: { x: number; y: number };
  /** Current local player facing direction. */
  playerDirection: PlayerDirection;
  /** Whether the local player is currently walking. */
  isPlayerWalking: boolean;
  /** WebSocket URL builder (e.g. wsUrl from App). */
  wsUrlBuilder: (path: string) => string;
  /** Optional player name override (persisted externally). */
  playerName?: string;
  /** Optional player color override (persisted externally). Empty = auto from clientID. */
  playerColor?: string;
};

export type RemoteCursor = {
  player_id: string;
  name: string;
  color: string;
  x: number;
  y: number;
};

export type UseMultiplayerReturn = {
  remotePlayers: RemotePlayer[];
  remoteEmotes: Record<string, string>;
  remoteChats: Record<string, string>;
  localEmote: string | null;
  localChat: string | null;
  /** The resolved local player name (chosen name or auto-assigned "Player N"). */
  localPlayerName: string;
  /** Whether the local player is idle (no movement for IDLE_TIMEOUT_MS). */
  isLocalIdle: boolean;
  connectionStatus: ConnectionStatus;
  /** Accumulated chat history (local + remote), newest last. */
  chatHistory: ChatMessage[];
  /** Remote players' typing state keyed by player_id. */
  remoteTyping: Record<string, boolean>;
  /** Whether the local player is currently typing. */
  isLocalTyping: boolean;
  /** Trigger a local emote by key ("1"–"4"). */
  triggerEmote: (key: string) => void;
  /** Send a chat message that appears as a bubble above the local player. */
  sendChat: (message: string) => void;
  /** Update the local typing state (call on chat input focus/change/blur). */
  setTyping: (typing: boolean) => void;
  /** Whether chat is on cooldown (true = cannot send yet). */
  chatOnCooldown: boolean;
  /** Number of reconnection attempts since last successful connection. */
  reconnectAttempts: number;
  /** Shared world decorations (persisted via Y.Map). */
  decorations: WorldDecoration[];
  /** Place an emoji decoration at a scene position. */
  placeDecoration: (emoji: string, x: number, y: number) => void;
  /** Remove all decorations from the world. */
  clearDecorations: () => void;
  /** Whether decoration placement is on cooldown (true = cannot place yet). */
  decoOnCooldown: boolean;
  /** Remote players' cursor positions (null when cursor is outside scene). */
  remoteCursors: RemoteCursor[];
  /** Update the local cursor position. Pass null when the mouse leaves the scene. */
  updateCursor: (position: CursorPosition | null) => void;
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PLAYER_NAME_STORAGE_KEY = "helping_hands_player_name_v1";
const PLAYER_COLOR_STORAGE_KEY = "helping_hands_player_color_v1";

/** Read persisted player name from localStorage. */
export function loadPlayerName(): string {
  try {
    return localStorage.getItem(PLAYER_NAME_STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

/** Persist player name to localStorage. */
export function savePlayerName(name: string): void {
  try {
    localStorage.setItem(PLAYER_NAME_STORAGE_KEY, name);
  } catch {
    // Ignore storage errors (private browsing, quota, etc.)
  }
}

/** Read persisted player color from localStorage. Empty string means use default. */
export function loadPlayerColor(): string {
  try {
    return localStorage.getItem(PLAYER_COLOR_STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

/** Persist player color to localStorage. */
export function savePlayerColor(color: string): void {
  try {
    localStorage.setItem(PLAYER_COLOR_STORAGE_KEY, color);
  } catch {
    // Ignore storage errors (private browsing, quota, etc.)
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useMultiplayer(options: UseMultiplayerOptions): UseMultiplayerReturn {
  const {
    active,
    playerPosition,
    playerDirection,
    isPlayerWalking,
    wsUrlBuilder,
    playerName,
    playerColor,
  } = options;

  const [remotePlayers, setRemotePlayers] = useState<RemotePlayer[]>([]);
  const [remoteEmotes, setRemoteEmotes] = useState<Record<string, string>>({});
  const [remoteChats, setRemoteChats] = useState<Record<string, string>>({});
  const [localEmote, setLocalEmote] = useState<string | null>(null);
  const [localChat, setLocalChat] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isLocalIdle, setIsLocalIdle] = useState(false);
  const [isLocalTyping, setIsLocalTyping] = useState(false);
  const [remoteTyping, setRemoteTyping] = useState<Record<string, boolean>>({});
  const [chatOnCooldown, setChatOnCooldown] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [decorations, setDecorations] = useState<WorldDecoration[]>([]);
  const [decoOnCooldown, setDecoOnCooldown] = useState(false);
  const [remoteCursors, setRemoteCursors] = useState<RemoteCursor[]>([]);
  const [localPlayerName, setLocalPlayerName] = useState(playerName?.trim() || "Player");

  const yjsDocRef = useRef<Y.Doc | null>(null);
  const yjsProviderRef = useRef<WebsocketProvider | null>(null);
  /** Track which remote chat texts we have already recorded, keyed by `clientId:text:seq`. */
  const seenRemoteChatsRef = useRef<Set<string>>(new Set());
  /** Sequence counter per player for chat dedup — allows same text to be recorded multiple times. */
  const chatSeqRef = useRef<Map<string, number>>(new Map());
  /** Cache player names/colors from awareness updates so leave messages show real names. */
  const playerNamesRef = useRef<Map<number, { name: string; color: string }>>(new Map());
  /** Timestamp of last local movement activity. */
  const lastActivityRef = useRef<number>(Date.now());
  /** Timestamp of last position broadcast (for throttling). */
  const lastBroadcastRef = useRef<number>(0);
  /** Handle for the pending throttled broadcast. */
  const broadcastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Timestamp of last cursor broadcast (for throttling). */
  const lastCursorBroadcastRef = useRef<number>(0);
  /** Handle for the pending throttled cursor broadcast. */
  const cursorBroadcastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Handle for the pending emote display clear timeout. */
  const emoteTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Handle for the pending emote awareness clear timeout. */
  const emoteAwarenessTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Handle for the pending chat display clear timeout. */
  const chatDisplayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Handle for the pending chat awareness clear timeout. */
  const chatAwarenessTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Handle for the pending chat cooldown clear timeout. */
  const chatCooldownTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Handle for the pending decoration placement cooldown clear timeout. */
  const decoCooldownTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // --- Connection lifecycle ---
  useEffect(() => {
    if (!active) {
      if (yjsProviderRef.current) {
        yjsProviderRef.current.destroy();
        yjsProviderRef.current = null;
      }
      if (yjsDocRef.current) {
        yjsDocRef.current.destroy();
        yjsDocRef.current = null;
      }
      setRemotePlayers([]);
      setChatHistory([]);
      setDecorations([]);
      setRemoteCursors([]);
      seenRemoteChatsRef.current.clear();
      chatSeqRef.current.clear();
      playerNamesRef.current.clear();
      setConnectionStatus("disconnected");
      setIsLocalIdle(false);
      setReconnectAttempts(0);
      return;
    }

    const doc = new Y.Doc();
    yjsDocRef.current = doc;

    const defaultColor = PLAYER_COLORS[doc.clientID % PLAYER_COLORS.length];
    const myColor = playerColor?.trim() || defaultColor;
    const defaultName = `Player ${(doc.clientID % 1000) + 1}`;
    const myName = playerName?.trim() || defaultName;
    setLocalPlayerName(myName);
    const myId = String(doc.clientID);

    const wsBase = wsUrlBuilder("/ws/yjs").replace(/\/$/, "");
    const provider = new WebsocketProvider(wsBase, "hand-world", doc);
    yjsProviderRef.current = provider;

    const onStatus = ({ status }: { status: string }) => {
      if (status === "connected") {
        setReconnectAttempts(0);
        setConnectionStatus("connected");
      } else if (status === "disconnected") {
        setReconnectAttempts((prev) => {
          const next = prev + 1;
          if (next >= MAX_RECONNECT_ATTEMPTS) {
            provider.disconnect();
            setConnectionStatus("failed");
            return next;
          }
          setConnectionStatus("connecting");
          return next;
        });
      } else {
        setConnectionStatus(status as ConnectionStatus);
      }
    };
    provider.on("status", onStatus);

    provider.awareness.setLocalStateField("player", {
      player_id: myId,
      name: myName,
      color: myColor,
      x: playerPosition.x,
      y: playerPosition.y,
      direction: playerDirection,
      walking: isPlayerWalking,
      idle: false,
      typing: false,
      emote: null,
      chat: null,
    });

    const onAwarenessChange = (
      changes: { added: number[]; updated: number[]; removed: number[] },
    ) => {
      const states = provider.awareness.getStates();
      const others: RemotePlayer[] = [];
      const newEmotes: Record<string, string> = {};
      const newChats: Record<string, string> = {};
      const newTyping: Record<string, boolean> = {};
      const cursors: RemoteCursor[] = [];

      states.forEach((state: Record<string, unknown>, clientId: number) => {
        if (clientId === doc.clientID) return;
        const p = state.player as (RemotePlayer & { emote?: string | null; chat?: string | null; typing?: boolean; cursor?: CursorPosition | null }) | undefined;
        if (!p) return;
        const pid = p.player_id ?? String(clientId);
        const resolvedName = p.name ?? `Player ${(clientId % 1000) + 1}`;
        const resolvedColor = p.color ?? PLAYER_COLORS[clientId % PLAYER_COLORS.length];
        // Cache name/color for leave messages (state is gone by the time `removed` fires).
        playerNamesRef.current.set(clientId, { name: resolvedName, color: resolvedColor });
        others.push({
          player_id: pid,
          name: resolvedName,
          color: resolvedColor,
          x: p.x ?? 50,
          y: p.y ?? 50,
          direction: (p.direction ?? "down") as PlayerDirection,
          walking: p.walking ?? false,
          idle: p.idle ?? false,
          typing: p.typing ?? false,
        });
        if (p.typing) {
          newTyping[pid] = true;
        }
        if (p.emote) {
          newEmotes[pid] = p.emote;
        }
        if (p.chat) {
          newChats[pid] = p.chat;
        }
        if (p.cursor && typeof p.cursor.x === "number" && typeof p.cursor.y === "number") {
          cursors.push({
            player_id: pid,
            name: resolvedName,
            color: resolvedColor,
            x: p.cursor.x,
            y: p.cursor.y,
          });
        }
      });

      setRemotePlayers(others);
      setRemoteEmotes(newEmotes);
      setRemoteChats(newChats);
      setRemoteTyping(newTyping);
      setRemoteCursors(cursors);

      // --- Join/leave system messages ---
      for (const clientId of changes.added) {
        if (clientId === doc.clientID) continue;
        const state = states.get(clientId) as Record<string, unknown> | undefined;
        const p = state?.player as Record<string, unknown> | undefined;
        const name = (p?.name as string) ?? `Player ${(clientId % 1000) + 1}`;
        const color = (p?.color as string) ?? PLAYER_COLORS[clientId % PLAYER_COLORS.length];
        setChatHistory((prev) => {
          const msg: ChatMessage = {
            id: `sys-join-${clientId}-${Date.now()}`,
            playerName: name,
            playerColor: color,
            text: `${name} joined`,
            timestamp: Date.now(),
            isSystem: true,
          };
          const next = [...prev, msg];
          return next.length > CHAT_HISTORY_MAX ? next.slice(-CHAT_HISTORY_MAX) : next;
        });
      }

      for (const clientId of changes.removed) {
        if (clientId === doc.clientID) continue;
        // Use cached name/color — state is already removed by the time `removed` fires.
        const cached = playerNamesRef.current.get(clientId);
        const name = cached?.name ?? `Player ${(clientId % 1000) + 1}`;
        const color = cached?.color ?? PLAYER_COLORS[clientId % PLAYER_COLORS.length];
        playerNamesRef.current.delete(clientId);
        setChatHistory((prev) => {
          const msg: ChatMessage = {
            id: `sys-leave-${clientId}-${Date.now()}`,
            playerName: name,
            playerColor: color,
            text: `${name} left`,
            timestamp: Date.now(),
            isSystem: true,
          };
          const next = [...prev, msg];
          return next.length > CHAT_HISTORY_MAX ? next.slice(-CHAT_HISTORY_MAX) : next;
        });
      }

      // Record new remote chat messages into history.
      // Dedup key uses pid:text:seq so the same text sent again (after the
      // previous bubble expired) is still recorded as a new message.
      for (const [pid, text] of Object.entries(newChats)) {
        const seq = chatSeqRef.current.get(pid) ?? 0;
        const dedupeKey = `${pid}:${text}:${seq}`;
        if (!seenRemoteChatsRef.current.has(dedupeKey)) {
          seenRemoteChatsRef.current.add(dedupeKey);
          const sender = others.find((o) => o.player_id === pid);
          setChatHistory((prev) => {
            const msg: ChatMessage = {
              id: `${pid}-${Date.now()}`,
              playerName: sender?.name ?? `Player ${pid}`,
              playerColor: sender?.color ?? PLAYER_COLORS[0],
              text,
              timestamp: Date.now(),
            };
            const next = [...prev, msg];
            return next.length > CHAT_HISTORY_MAX ? next.slice(-CHAT_HISTORY_MAX) : next;
          });
        }
      }

      // Clean dedupe keys for chats that are no longer active — bump the
      // sequence counter so the next identical message gets a fresh key.
      for (const key of seenRemoteChatsRef.current) {
        const parts = key.split(":");
        const pid = parts[0];
        if (!newChats[pid]) {
          seenRemoteChatsRef.current.delete(key);
          chatSeqRef.current.set(pid, (chatSeqRef.current.get(pid) ?? 0) + 1);
        }
      }
    };

    provider.awareness.on("change", onAwarenessChange);

    // --- Shared decoration map (persistent Y.Doc state) ---
    const decoMap = doc.getMap("decorations");
    const syncDecorations = () => {
      const items: WorldDecoration[] = [];
      decoMap.forEach((value: unknown, key: string) => {
        const d = value as WorldDecoration | undefined;
        if (d && d.emoji) {
          items.push({ ...d, id: key });
        }
      });
      items.sort((a, b) => a.placedAt - b.placedAt);
      setDecorations(items);
    };
    decoMap.observe(syncDecorations);
    syncDecorations();

    return () => {
      decoMap.unobserve(syncDecorations);
      provider.off("status", onStatus);
      provider.awareness.off("change", onAwarenessChange);
      provider.destroy();
      doc.destroy();
      yjsProviderRef.current = null;
      yjsDocRef.current = null;
      setConnectionStatus("disconnected");
      setReconnectAttempts(0);
      // Clear any pending emote/chat/cooldown timers to prevent state
      // updates after the provider is destroyed or the component unmounts.
      for (const ref of [emoteTimerRef, emoteAwarenessTimerRef, chatDisplayTimerRef, chatAwarenessTimerRef, chatCooldownTimerRef, decoCooldownTimerRef]) {
        if (ref.current) {
          clearTimeout(ref.current);
          ref.current = null;
        }
      }
    };
    // playerName is intentionally omitted — name updates are handled by the
    // separate effect below to avoid reconnecting the provider on every keystroke.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, wsUrlBuilder]);

  // --- Broadcast player name changes without reconnecting ---
  useEffect(() => {
    if (!active) return;
    const provider = yjsProviderRef.current;
    if (!provider) return;

    const current = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
    if (!current) return;

    const defaultName = yjsDocRef.current
      ? `Player ${(yjsDocRef.current.clientID % 1000) + 1}`
      : "Player";
    const name = playerName?.trim() || defaultName;
    setLocalPlayerName(name);

    if (current.name !== name) {
      provider.awareness.setLocalStateField("player", { ...current, name });
    }
  }, [active, playerName]);

  // --- Broadcast player color changes without reconnecting ---
  useEffect(() => {
    if (!active) return;
    const provider = yjsProviderRef.current;
    if (!provider) return;

    const current = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
    if (!current) return;

    const defaultColor = yjsDocRef.current
      ? PLAYER_COLORS[yjsDocRef.current.clientID % PLAYER_COLORS.length]
      : PLAYER_COLORS[0];
    const color = playerColor?.trim() || defaultColor;

    if (current.color !== color) {
      provider.awareness.setLocalStateField("player", { ...current, color });
    }
  }, [active, playerColor]);

  // --- Send local position updates & track activity (throttled) ---
  useEffect(() => {
    if (!active) return;

    // Any position/direction/walking change counts as activity.
    lastActivityRef.current = Date.now();
    if (isLocalIdle) {
      setIsLocalIdle(false);
    }

    const doBroadcast = () => {
      const provider = yjsProviderRef.current;
      if (!provider) return;
      const current = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
      if (!current) return;
      provider.awareness.setLocalStateField("player", {
        ...current,
        x: playerPosition.x,
        y: playerPosition.y,
        direction: playerDirection,
        walking: isPlayerWalking,
        idle: false,
      });
      lastBroadcastRef.current = Date.now();
    };

    const elapsed = Date.now() - lastBroadcastRef.current;
    if (elapsed >= POSITION_BROADCAST_INTERVAL_MS) {
      // Enough time has passed — broadcast immediately.
      if (broadcastTimerRef.current) {
        clearTimeout(broadcastTimerRef.current);
        broadcastTimerRef.current = null;
      }
      doBroadcast();
    } else if (!broadcastTimerRef.current) {
      // Schedule a trailing broadcast for the remaining interval.
      broadcastTimerRef.current = setTimeout(() => {
        broadcastTimerRef.current = null;
        doBroadcast();
      }, POSITION_BROADCAST_INTERVAL_MS - elapsed);
    }

    return () => {
      if (broadcastTimerRef.current) {
        clearTimeout(broadcastTimerRef.current);
        broadcastTimerRef.current = null;
      }
    };
  }, [active, playerPosition, playerDirection, isPlayerWalking]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Idle detection timer ---
  useEffect(() => {
    if (!active) return;

    const checkIdle = () => {
      const elapsed = Date.now() - lastActivityRef.current;
      const idle = elapsed >= IDLE_TIMEOUT_MS;

      setIsLocalIdle((prev) => {
        if (prev === idle) return prev;

        // Broadcast idle state change.
        const provider = yjsProviderRef.current;
        if (provider) {
          const current = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
          if (current) {
            provider.awareness.setLocalStateField("player", { ...current, idle });
          }
        }
        return idle;
      });
    };

    const intervalId = setInterval(checkIdle, 5000);
    return () => clearInterval(intervalId);
  }, [active]);

  // --- Emote trigger callback ---
  const triggerEmote = useCallback(
    (key: string) => {
      const emote = EMOTE_KEY_BINDINGS[key];
      if (!emote) return;

      setLocalEmote(emote);
      if (emoteTimerRef.current) clearTimeout(emoteTimerRef.current);
      emoteTimerRef.current = setTimeout(() => {
        emoteTimerRef.current = null;
        setLocalEmote(null);
      }, EMOTE_DISPLAY_MS);

      const provider = yjsProviderRef.current;
      if (provider) {
        const current = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
        if (current) {
          provider.awareness.setLocalStateField("player", { ...current, emote });
          if (emoteAwarenessTimerRef.current) clearTimeout(emoteAwarenessTimerRef.current);
          emoteAwarenessTimerRef.current = setTimeout(() => {
            emoteAwarenessTimerRef.current = null;
            const latest = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
            if (latest) {
              provider.awareness.setLocalStateField("player", { ...latest, emote: null });
            }
          }, EMOTE_DISPLAY_MS);
        }
      }
    },
    [],
  );

  // --- Chat send callback ---
  const sendChat = useCallback(
    (message: string) => {
      const text = message.trim();
      if (!text) return;
      if (chatOnCooldown) return;

      // Start cooldown.
      setChatOnCooldown(true);
      if (chatCooldownTimerRef.current) clearTimeout(chatCooldownTimerRef.current);
      chatCooldownTimerRef.current = setTimeout(() => {
        chatCooldownTimerRef.current = null;
        setChatOnCooldown(false);
      }, CHAT_COOLDOWN_MS);

      setLocalChat(text);
      if (chatDisplayTimerRef.current) clearTimeout(chatDisplayTimerRef.current);
      chatDisplayTimerRef.current = setTimeout(() => {
        chatDisplayTimerRef.current = null;
        setLocalChat(null);
      }, CHAT_DISPLAY_MS);

      const provider = yjsProviderRef.current;

      // Record local message in chat history.
      const doc = yjsDocRef.current;
      const myId = doc ? String(doc.clientID) : "local";
      const localState = provider?.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
      setChatHistory((prev) => {
        const msg: ChatMessage = {
          id: `${myId}-${Date.now()}`,
          playerName: (localState?.name as string) ?? "You",
          playerColor: (localState?.color as string) ?? PLAYER_COLORS[0],
          text,
          timestamp: Date.now(),
        };
        const next = [...prev, msg];
        return next.length > CHAT_HISTORY_MAX ? next.slice(-CHAT_HISTORY_MAX) : next;
      });
      if (provider) {
        const current = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
        if (current) {
          provider.awareness.setLocalStateField("player", { ...current, chat: text });
          if (chatAwarenessTimerRef.current) clearTimeout(chatAwarenessTimerRef.current);
          chatAwarenessTimerRef.current = setTimeout(() => {
            chatAwarenessTimerRef.current = null;
            const latest = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
            if (latest) {
              provider.awareness.setLocalStateField("player", { ...latest, chat: null });
            }
          }, CHAT_DISPLAY_MS);
        }
      }
    },
    [chatOnCooldown],
  );

  // --- Typing state callback ---
  const setTyping = useCallback(
    (typing: boolean) => {
      setIsLocalTyping(typing);
      const provider = yjsProviderRef.current;
      if (provider) {
        const current = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
        if (current) {
          provider.awareness.setLocalStateField("player", { ...current, typing });
        }
      }
    },
    [],
  );

  // --- Place decoration callback ---
  const placeDecoration = useCallback(
    (emoji: string, x: number, y: number) => {
      if (decoOnCooldown) return;

      const doc = yjsDocRef.current;
      if (!doc) return;
      const decoMap = doc.getMap("decorations");
      if (decoMap.size >= MAX_DECORATIONS) return;

      // Start cooldown.
      setDecoOnCooldown(true);
      if (decoCooldownTimerRef.current) clearTimeout(decoCooldownTimerRef.current);
      decoCooldownTimerRef.current = setTimeout(() => {
        decoCooldownTimerRef.current = null;
        setDecoOnCooldown(false);
      }, DECO_COOLDOWN_MS);

      const provider = yjsProviderRef.current;
      const localState = provider?.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
      const id = `${doc.clientID}-${Date.now()}`;
      decoMap.set(id, {
        id,
        emoji,
        x,
        y,
        placedBy: (localState?.name as string) ?? "Unknown",
        color: (localState?.color as string) ?? PLAYER_COLORS[0],
        placedAt: Date.now(),
      });
    },
    [decoOnCooldown],
  );

  // --- Clear decorations callback ---
  const clearDecorations = useCallback(() => {
    const doc = yjsDocRef.current;
    if (!doc) return;
    const decoMap = doc.getMap("decorations");
    doc.transact(() => {
      const keys = Array.from(decoMap.keys());
      for (const key of keys) {
        decoMap.delete(key);
      }
    });
  }, []);

  // --- Cursor update callback (throttled) ---
  const updateCursor = useCallback(
    (position: CursorPosition | null) => {
      // Clamp cursor coordinates to [0, 100] to match backend validation.
      const clamped = position
        ? { x: Math.max(0, Math.min(100, position.x)), y: Math.max(0, Math.min(100, position.y)) }
        : null;

      const doBroadcast = () => {
        const provider = yjsProviderRef.current;
        if (!provider) return;
        const current = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
        if (!current) return;
        provider.awareness.setLocalStateField("player", { ...current, cursor: clamped });
        lastCursorBroadcastRef.current = Date.now();
      };

      // Null (mouse left scene) — broadcast immediately.
      if (position === null) {
        if (cursorBroadcastTimerRef.current) {
          clearTimeout(cursorBroadcastTimerRef.current);
          cursorBroadcastTimerRef.current = null;
        }
        doBroadcast();
        return;
      }

      const elapsed = Date.now() - lastCursorBroadcastRef.current;
      if (elapsed >= CURSOR_BROADCAST_INTERVAL_MS) {
        if (cursorBroadcastTimerRef.current) {
          clearTimeout(cursorBroadcastTimerRef.current);
          cursorBroadcastTimerRef.current = null;
        }
        doBroadcast();
      } else if (!cursorBroadcastTimerRef.current) {
        cursorBroadcastTimerRef.current = setTimeout(() => {
          cursorBroadcastTimerRef.current = null;
          doBroadcast();
        }, CURSOR_BROADCAST_INTERVAL_MS - elapsed);
      }
    },
    [],
  );

  // --- Emote key bindings ---
  useEffect(() => {
    if (!active) return;

    const handleEmoteKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isTyping =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable;
      if (isTyping) return;

      if (EMOTE_KEY_BINDINGS[event.key]) {
        triggerEmote(event.key);
      }
    };

    window.addEventListener("keydown", handleEmoteKey);
    return () => window.removeEventListener("keydown", handleEmoteKey);
  }, [active, triggerEmote]);

  return {
    remotePlayers,
    remoteEmotes,
    remoteChats,
    remoteTyping,
    localEmote,
    localChat,
    localPlayerName,
    isLocalIdle,
    isLocalTyping,
    connectionStatus,
    chatHistory,
    triggerEmote,
    sendChat,
    setTyping,
    chatOnCooldown,
    reconnectAttempts,
    decoOnCooldown,
    decorations,
    placeDecoration,
    clearDecorations,
    remoteCursors,
    updateCursor,
  };
}
