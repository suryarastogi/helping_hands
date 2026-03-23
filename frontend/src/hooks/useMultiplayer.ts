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
  EMOTE_DISPLAY_MS,
  EMOTE_KEY_BINDINGS,
  PLAYER_COLORS,
} from "../App";
import type { PlayerDirection } from "../types";

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
  localEmote: string | null;
  connectionStatus: ConnectionStatus;
  /** Trigger a local emote by key ("1"–"4"). */
  triggerEmote: (key: string) => void;
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
  const [localEmote, setLocalEmote] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");

  const yjsDocRef = useRef<Y.Doc | null>(null);
  const yjsProviderRef = useRef<WebsocketProvider | null>(null);

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
      setConnectionStatus("disconnected");
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
      emote: null,
    });

    const onAwarenessChange = () => {
      const states = provider.awareness.getStates();
      const others: RemotePlayer[] = [];
      const newEmotes: Record<string, string> = {};

      states.forEach((state: Record<string, unknown>, clientId: number) => {
        if (clientId === doc.clientID) return;
        const p = state.player as (RemotePlayer & { emote?: string | null }) | undefined;
        if (!p) return;
        others.push({
          player_id: p.player_id ?? String(clientId),
          name: p.name ?? `Player ${(clientId % 1000) + 1}`,
          color: p.color ?? PLAYER_COLORS[clientId % PLAYER_COLORS.length],
          x: p.x ?? 50,
          y: p.y ?? 50,
          direction: (p.direction ?? "down") as PlayerDirection,
          walking: p.walking ?? false,
        });
        if (p.emote) {
          newEmotes[p.player_id ?? String(clientId)] = p.emote;
        }
      });

      setRemotePlayers(others);
      setRemoteEmotes(newEmotes);
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

  // --- Send local position updates ---
  useEffect(() => {
    if (!active) return;
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
    });
  }, [active, playerPosition, playerDirection, isPlayerWalking]);

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
    localEmote,
    connectionStatus,
    triggerEmote,
  };
}
