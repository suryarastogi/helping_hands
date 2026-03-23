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
  CHAT_DISPLAY_MS,
  CHAT_HISTORY_MAX,
  EMOTE_DISPLAY_MS,
  EMOTE_KEY_BINDINGS,
  IDLE_TIMEOUT_MS,
  PLAYER_COLORS,
} from "../constants";
import type { ChatMessage, PlayerDirection } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ConnectionStatus = "disconnected" | "connecting" | "connected";

export type RemotePlayer = {
  player_id: string;
  name: string;
  color: string;
  x: number;
  y: number;
  direction: PlayerDirection;
  walking: boolean;
  idle: boolean;
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
};

export type UseMultiplayerReturn = {
  remotePlayers: RemotePlayer[];
  remoteEmotes: Record<string, string>;
  remoteChats: Record<string, string>;
  localEmote: string | null;
  localChat: string | null;
  /** Whether the local player is idle (no movement for IDLE_TIMEOUT_MS). */
  isLocalIdle: boolean;
  connectionStatus: ConnectionStatus;
  /** Accumulated chat history (local + remote), newest last. */
  chatHistory: ChatMessage[];
  /** Trigger a local emote by key ("1"–"4"). */
  triggerEmote: (key: string) => void;
  /** Send a chat message that appears as a bubble above the local player. */
  sendChat: (message: string) => void;
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PLAYER_NAME_STORAGE_KEY = "helping_hands_player_name_v1";

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
  } = options;

  const [remotePlayers, setRemotePlayers] = useState<RemotePlayer[]>([]);
  const [remoteEmotes, setRemoteEmotes] = useState<Record<string, string>>({});
  const [remoteChats, setRemoteChats] = useState<Record<string, string>>({});
  const [localEmote, setLocalEmote] = useState<string | null>(null);
  const [localChat, setLocalChat] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isLocalIdle, setIsLocalIdle] = useState(false);

  const yjsDocRef = useRef<Y.Doc | null>(null);
  const yjsProviderRef = useRef<WebsocketProvider | null>(null);
  /** Track which remote chat texts we have already recorded, keyed by `clientId:text`. */
  const seenRemoteChatsRef = useRef<Set<string>>(new Set());
  /** Timestamp of last local movement activity. */
  const lastActivityRef = useRef<number>(Date.now());

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
      seenRemoteChatsRef.current.clear();
      setConnectionStatus("disconnected");
      setIsLocalIdle(false);
      return;
    }

    const doc = new Y.Doc();
    yjsDocRef.current = doc;

    const myColor = PLAYER_COLORS[doc.clientID % PLAYER_COLORS.length];
    const defaultName = `Player ${(doc.clientID % 1000) + 1}`;
    const myName = playerName?.trim() || defaultName;
    const myId = String(doc.clientID);

    const wsBase = wsUrlBuilder("/ws/yjs").replace(/\/$/, "");
    const provider = new WebsocketProvider(wsBase, "hand-world", doc);
    yjsProviderRef.current = provider;

    const onStatus = ({ status }: { status: string }) => {
      setConnectionStatus(status as ConnectionStatus);
    };
    provider.on("status", onStatus);

    provider.awareness.setLocalStateField("player", {
      player_id: myId,
      name: myName,
      color: myColor,
      x: 50,
      y: 50,
      direction: "down",
      walking: false,
      idle: false,
      emote: null,
      chat: null,
    });

    const onAwarenessChange = () => {
      const states = provider.awareness.getStates();
      const others: RemotePlayer[] = [];
      const newEmotes: Record<string, string> = {};
      const newChats: Record<string, string> = {};

      states.forEach((state: Record<string, unknown>, clientId: number) => {
        if (clientId === doc.clientID) return;
        const p = state.player as (RemotePlayer & { emote?: string | null; chat?: string | null }) | undefined;
        if (!p) return;
        const pid = p.player_id ?? String(clientId);
        others.push({
          player_id: pid,
          name: p.name ?? `Player ${(clientId % 1000) + 1}`,
          color: p.color ?? PLAYER_COLORS[clientId % PLAYER_COLORS.length],
          x: p.x ?? 50,
          y: p.y ?? 50,
          direction: (p.direction ?? "down") as PlayerDirection,
          walking: p.walking ?? false,
          idle: p.idle ?? false,
        });
        if (p.emote) {
          newEmotes[pid] = p.emote;
        }
        if (p.chat) {
          newChats[pid] = p.chat;
        }
      });

      setRemotePlayers(others);
      setRemoteEmotes(newEmotes);
      setRemoteChats(newChats);

      // Record new remote chat messages into history.
      for (const [pid, text] of Object.entries(newChats)) {
        const dedupeKey = `${pid}:${text}`;
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

      // Clean dedupe keys for chats that are no longer active.
      for (const key of seenRemoteChatsRef.current) {
        const [pid] = key.split(":");
        if (!newChats[pid]) {
          seenRemoteChatsRef.current.delete(key);
        }
      }
    };

    provider.awareness.on("change", onAwarenessChange);

    return () => {
      provider.off("status", onStatus);
      provider.awareness.off("change", onAwarenessChange);
      provider.destroy();
      doc.destroy();
      yjsProviderRef.current = null;
      yjsDocRef.current = null;
      setConnectionStatus("disconnected");
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

    if (current.name !== name) {
      provider.awareness.setLocalStateField("player", { ...current, name });
    }
  }, [active, playerName]);

  // --- Send local position updates & track activity ---
  useEffect(() => {
    if (!active) return;
    const provider = yjsProviderRef.current;
    if (!provider) return;

    const current = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
    if (!current) return;

    // Any position/direction/walking change counts as activity.
    lastActivityRef.current = Date.now();
    if (isLocalIdle) {
      setIsLocalIdle(false);
    }

    provider.awareness.setLocalStateField("player", {
      ...current,
      x: playerPosition.x,
      y: playerPosition.y,
      direction: playerDirection,
      walking: isPlayerWalking,
      idle: false,
    });
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
      setTimeout(() => setLocalEmote(null), EMOTE_DISPLAY_MS);

      const provider = yjsProviderRef.current;
      if (provider) {
        const current = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
        if (current) {
          provider.awareness.setLocalStateField("player", { ...current, emote });
          setTimeout(() => {
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

      setLocalChat(text);
      setTimeout(() => setLocalChat(null), CHAT_DISPLAY_MS);

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
          setTimeout(() => {
            const latest = provider.awareness.getLocalState()?.player as Record<string, unknown> | undefined;
            if (latest) {
              provider.awareness.setLocalStateField("player", { ...latest, chat: null });
            }
          }, CHAT_DISPLAY_MS);
        }
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
    localEmote,
    localChat,
    isLocalIdle,
    connectionStatus,
    chatHistory,
    triggerEmote,
    sendChat,
  };
}
