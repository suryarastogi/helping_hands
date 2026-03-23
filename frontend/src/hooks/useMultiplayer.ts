/**
 * useMultiplayer — Yjs awareness-based multiplayer presence for Hand World.
 *
 * Manages the Yjs document/provider lifecycle, tracks remote player positions
 * via the awareness protocol, and broadcasts local player state + emotes.
 */

import { useEffect, useRef, useState } from "react";
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";
import { wsUrl } from "../App";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PlayerDirection = "down" | "up" | "left" | "right";

export type RemotePlayer = {
  player_id: string;
  name: string;
  color: string;
  x: number;
  y: number;
  direction: PlayerDirection;
  walking: boolean;
};

export type YjsConnectionStatus = "disconnected" | "connecting" | "connected";

export type MultiplayerState = {
  remotePlayers: RemotePlayer[];
  remoteEmotes: Record<string, string>;
  localEmote: string | null;
  yjsConnStatus: YjsConnectionStatus;
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const PLAYER_COLORS = [
  "#e11d48", "#2563eb", "#16a34a", "#d97706", "#7c3aed",
  "#0891b2", "#dc2626", "#4f46e5", "#059669", "#c026d3",
];

export const EMOTE_MAP: Record<string, string> = {
  wave: "\u{1F44B}",
  celebrate: "\u{1F389}",
  thumbsup: "\u{1F44D}",
  sparkle: "\u{2728}",
};

export const EMOTE_KEY_BINDINGS: Record<string, string> = {
  "1": "wave",
  "2": "celebrate",
  "3": "thumbsup",
  "4": "sparkle",
};

export const EMOTE_DISPLAY_MS = 2000;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface UseMultiplayerOptions {
  /** Whether the world view is active. Connection is only established when true. */
  active: boolean;
  /** Current local player position. */
  playerPosition: { x: number; y: number };
  /** Current local player facing direction. */
  playerDirection: PlayerDirection;
  /** Whether the local player is currently walking. */
  isPlayerWalking: boolean;
}

export function useMultiplayer({
  active,
  playerPosition,
  playerDirection,
  isPlayerWalking,
}: UseMultiplayerOptions): MultiplayerState {
  const [remotePlayers, setRemotePlayers] = useState<RemotePlayer[]>([]);
  const [remoteEmotes, setRemoteEmotes] = useState<Record<string, string>>({});
  const [localEmote, setLocalEmote] = useState<string | null>(null);
  const [yjsConnStatus, setYjsConnStatus] = useState<YjsConnectionStatus>("disconnected");

  const yjsDocRef = useRef<Y.Doc | null>(null);
  const yjsProviderRef = useRef<WebsocketProvider | null>(null);

  // --- Yjs connection lifecycle ---
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
      setYjsConnStatus("disconnected");
      return;
    }

    const doc = new Y.Doc();
    yjsDocRef.current = doc;

    const myColor = PLAYER_COLORS[doc.clientID % PLAYER_COLORS.length];
    const myName = `Player ${(doc.clientID % 1000) + 1}`;
    const myId = String(doc.clientID);

    const wsBase = wsUrl("/ws/yjs").replace(/\/$/, "");
    const provider = new WebsocketProvider(wsBase, "hand-world", doc);
    yjsProviderRef.current = provider;

    const onStatus = ({ status }: { status: string }) => {
      setYjsConnStatus(status as YjsConnectionStatus);
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
      setYjsConnStatus("disconnected");
    };
  }, [active]);

  // --- Send local position updates via Yjs awareness ---
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

  // --- Emote key bindings (1-4) via Yjs awareness ---
  useEffect(() => {
    if (!active) return;

    const handleEmoteKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isTyping =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable;
      if (isTyping) return;

      const emote = EMOTE_KEY_BINDINGS[event.key];
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
    };

    window.addEventListener("keydown", handleEmoteKey);
    return () => window.removeEventListener("keydown", handleEmoteKey);
  }, [active]);

  return { remotePlayers, remoteEmotes, localEmote, yjsConnStatus };
}
