/**
 * useMultiplayer — yjs awareness hook for Hand World multiplayer.
 *
 * Each browser tab creates a yjs Doc + WebsocketProvider connected to the
 * backend at `/ws/world`.  The awareness protocol broadcasts lightweight
 * presence state (position, direction, walking, color, name) to all peers.
 *
 * Remote peers are exposed as `RemotePlayer[]` which the Hand World scene
 * renders as additional player sprites.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Doc } from "yjs";
import { WebsocketProvider } from "y-websocket";

// ── Types ──────────────────────────────────────────────────────────────

export type PlayerDirection = "down" | "up" | "left" | "right";

export type LocalPlayerState = {
  position: { x: number; y: number };
  direction: PlayerDirection;
  walking: boolean;
};

export type RemotePlayer = {
  clientId: number;
  name: string;
  color: string;
  position: { x: number; y: number };
  direction: PlayerDirection;
  walking: boolean;
};

// ── Random identity helpers ────────────────────────────────────────────

const PLAYER_COLORS = [
  "#e74c3c", // red
  "#2ecc71", // green
  "#3498db", // blue
  "#f39c12", // orange
  "#9b59b6", // purple
  "#1abc9c", // teal
  "#e67e22", // dark orange
  "#e91e63", // pink
];

const PLAYER_NAMES = [
  "Explorer",
  "Builder",
  "Tinker",
  "Scout",
  "Ranger",
  "Spark",
  "Drift",
  "Pixel",
];

function randomChoice<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

// ── Hook ───────────────────────────────────────────────────────────────

export type UseMultiplayerOptions = {
  /** Whether multiplayer is active (e.g., world view is visible). */
  enabled: boolean;
  /** WebSocket URL override. Defaults to auto-detect from window.location. */
  wsUrl?: string;
};

export type UseMultiplayerReturn = {
  /** Remote players currently in the room. */
  remotePlayers: RemotePlayer[];
  /** Update the local player state to broadcast to peers. */
  updateLocalState: (state: LocalPlayerState) => void;
  /** Number of connected peers (including self). */
  connectionCount: number;
  /** Whether the WebSocket is currently connected. */
  connected: boolean;
};

/**
 * Build the default WebSocket URL from the current page location.
 * In dev (Vite proxy), use the VITE_API_BASE_URL env var if set.
 */
function defaultWsUrl(): string {
  const apiBase = (import.meta.env.VITE_API_BASE_URL ?? "").trim();
  if (apiBase) {
    // Convert http(s) URL to ws(s)
    const url = new URL(apiBase);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return url.toString().replace(/\/$/, "");
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}`;
}

export function useMultiplayer({
  enabled,
  wsUrl,
}: UseMultiplayerOptions): UseMultiplayerReturn {
  const [remotePlayers, setRemotePlayers] = useState<RemotePlayer[]>([]);
  const [connected, setConnected] = useState(false);
  const [connectionCount, setConnectionCount] = useState(0);

  // Stable identity for this tab (persists across re-renders, not across reloads).
  const identityRef = useRef({
    name: randomChoice(PLAYER_NAMES),
    color: randomChoice(PLAYER_COLORS),
  });

  const providerRef = useRef<WebsocketProvider | null>(null);
  const docRef = useRef<Doc | null>(null);

  const updateLocalState = useCallback((state: LocalPlayerState) => {
    const provider = providerRef.current;
    if (!provider) return;
    provider.awareness.setLocalStateField("player", {
      ...state,
      name: identityRef.current.name,
      color: identityRef.current.color,
    });
  }, []);

  useEffect(() => {
    if (!enabled) {
      // Cleanup if we were connected.
      if (providerRef.current) {
        providerRef.current.destroy();
        providerRef.current = null;
      }
      if (docRef.current) {
        docRef.current.destroy();
        docRef.current = null;
      }
      setRemotePlayers([]);
      setConnected(false);
      setConnectionCount(0);
      return;
    }

    const doc = new Doc();
    const base = wsUrl ?? defaultWsUrl();
    const provider = new WebsocketProvider(base, "world", doc, {
      connect: true,
    });

    docRef.current = doc;
    providerRef.current = provider;

    // Set initial awareness state.
    provider.awareness.setLocalStateField("player", {
      position: { x: 50, y: 50 },
      direction: "down" as PlayerDirection,
      walking: false,
      name: identityRef.current.name,
      color: identityRef.current.color,
    });

    const onAwarenessChange = () => {
      const states = provider.awareness.getStates();
      const localId = provider.awareness.clientID;
      const remote: RemotePlayer[] = [];

      states.forEach((state, clientId) => {
        if (clientId === localId) return;
        const p = state.player;
        if (!p || !p.position) return;
        remote.push({
          clientId,
          name: p.name ?? "Unknown",
          color: p.color ?? "#888",
          position: p.position,
          direction: p.direction ?? "down",
          walking: p.walking ?? false,
        });
      });

      setRemotePlayers(remote);
      setConnectionCount(states.size);
    };

    provider.awareness.on("change", onAwarenessChange);

    const onStatus = ({ status }: { status: string }) => {
      setConnected(status === "connected");
    };
    provider.on("status", onStatus);

    return () => {
      provider.awareness.off("change", onAwarenessChange);
      provider.off("status", onStatus);
      provider.destroy();
      doc.destroy();
      providerRef.current = null;
      docRef.current = null;
    };
  }, [enabled, wsUrl]);

  return { remotePlayers, updateLocalState, connectionCount, connected };
}
