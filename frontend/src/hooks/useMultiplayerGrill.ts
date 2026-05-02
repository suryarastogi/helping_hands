/**
 * useMultiplayerGrill — session actions + live subscription to the Yjs room.
 *
 * The backend state (``status``, ``creator_*``, ``turn_count``,
 * ``participant_count``) is polled from ``GET /mgrill/{id}`` at a slow
 * interval.  Transcript, pending batch, and votes live in the Yjs room
 * ``mgrill-{session_id}`` and are observed here via ``y-websocket``'s
 * ``WebsocketProvider``, so participants see AI turns, votes, and queued
 * messages with Yjs's native sub-100 ms latency — not polling lag.
 *
 * Mutations still go through REST endpoints (auth-gated, server re-checks
 * creator identity + vote tallies); those endpoints write to the same
 * in-process Y.Doc so the frontend sees the effect via its subscription.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";

import { apiUrl, wsUrl } from "../App.utils";
import type {
  MGrillCreateForm,
  MGrillCreateResponse,
  MGrillListResponse,
  MGrillMessage,
  MGrillPendingEntry,
  MGrillPollResponse,
  MGrillSessionSummary,
} from "../types";

const STATE_POLL_INTERVAL_MS = 3000;
const LOBBY_POLL_INTERVAL_MS = 3000;
const HEARTBEAT_INTERVAL_MS = 20_000;

export type MGrillSessionLiveState = {
  messages: MGrillMessage[];
  pending: MGrillPendingEntry[];
  votes: Record<string, "up" | "down">;
  finalPlan: string | null;
  /** True once the provider reports a synced connection. */
  yjsConnected: boolean;
};

export type MGrillSessionActions = {
  state: MGrillPollResponse | null;
  live: MGrillSessionLiveState;
  sessionId: string | null;
  error: string | null;
  isLoading: boolean;
  createSession: (form: MGrillCreateForm, creatorName: string) => Promise<string | null>;
  joinSession: (sessionId: string) => void;
  leaveSession: () => void;
  addPending: (content: string, playerId: string, playerName: string) => Promise<void>;
  removePending: (pendingId: string, playerId: string) => Promise<void>;
  sendToAi: () => Promise<void>;
  requestPlan: () => Promise<void>;
  castVote: (playerId: string, vote: "up" | "down" | "clear") => Promise<void>;
  submitPlan: (opts?: { override?: boolean }) => Promise<
    | { ok: true; task_id: string; override: boolean }
    | { ok: false; status: number; body: unknown }
  >;
  keepGrilling: () => Promise<void>;
  claimCreator: (playerId: string, playerName: string) => Promise<
    | { ok: true }
    | { ok: false; status: number; body: unknown }
  >;
};

function tokenHeaders(token: string | undefined, extra?: Record<string, string>): Record<string, string> {
  const base: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    base["X-GitHub-Token"] = token;
  }
  if (extra) {
    Object.assign(base, extra);
  }
  return base;
}

function coerceMessage(raw: unknown): MGrillMessage | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  if (typeof r.id !== "string" || typeof r.role !== "string") return null;
  return {
    id: r.id,
    role: r.role as MGrillMessage["role"],
    content: typeof r.content === "string" ? r.content : "",
    type: (typeof r.type === "string" ? r.type : "message") as MGrillMessage["type"],
    author_player_id:
      typeof r.author_player_id === "string" ? r.author_player_id : null,
    author_name: typeof r.author_name === "string" ? r.author_name : null,
    timestamp: typeof r.timestamp === "number" ? r.timestamp : 0,
  };
}

function coercePending(pendingId: string, raw: unknown): MGrillPendingEntry | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  if (typeof r.player_id !== "string") return null;
  return {
    pending_id: pendingId,
    player_id: r.player_id,
    name: typeof r.name === "string" ? r.name : "",
    content: typeof r.content === "string" ? r.content : "",
    timestamp: typeof r.timestamp === "number" ? r.timestamp : 0,
  };
}

export function useMultiplayerGrill(githubToken?: string): MGrillSessionActions {
  const tokenRef = useRef(githubToken);
  tokenRef.current = githubToken;

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<MGrillPollResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<MGrillMessage[]>([]);
  const [pending, setPending] = useState<MGrillPendingEntry[]>([]);
  const [votes, setVotes] = useState<Record<string, "up" | "down">>({});
  const [yjsConnected, setYjsConnected] = useState(false);

  const pollingRef = useRef<number | null>(null);
  const heartbeatRef = useRef<number | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const docRef = useRef<Y.Doc | null>(null);
  const providerRef = useRef<WebsocketProvider | null>(null);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  const stopPolling = useCallback(() => {
    if (pollingRef.current !== null) {
      window.clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const stopHeartbeat = useCallback(() => {
    if (heartbeatRef.current !== null) {
      window.clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }
  }, []);

  const tearDownYjs = useCallback(() => {
    if (providerRef.current) {
      providerRef.current.destroy();
      providerRef.current = null;
    }
    if (docRef.current) {
      docRef.current.destroy();
      docRef.current = null;
    }
    setMessages([]);
    setPending([]);
    setVotes({});
    setYjsConnected(false);
  }, []);

  const pollState = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;
    try {
      const res = await fetch(apiUrl(`/mgrill/${sid}?_=${Date.now()}`), {
        cache: "no-store",
        headers: tokenHeaders(tokenRef.current),
      });
      if (!res.ok) {
        if (res.status === 404) {
          setError("Session not found");
          stopPolling();
        }
        return;
      }
      const data = (await res.json()) as MGrillPollResponse;
      setState(data);
      if (
        data.status === "error" ||
        data.status === "max_turns"
      ) {
        stopPolling();
      }
    } catch {
      // transient error — keep polling
    }
  }, [stopPolling]);

  const startPolling = useCallback(() => {
    stopPolling();
    pollingRef.current = window.setInterval(
      () => void pollState(),
      STATE_POLL_INTERVAL_MS,
    );
    void pollState();
  }, [pollState, stopPolling]);

  // Connect to the Yjs room whenever we have an active session id.
  useEffect(() => {
    tearDownYjs();
    if (!sessionId) return;

    const doc = new Y.Doc();
    docRef.current = doc;
    const wsBase = wsUrl("/ws/yjs").replace(/\/$/, "");
    const provider = new WebsocketProvider(wsBase, `mgrill-${sessionId}`, doc);
    providerRef.current = provider;

    const onStatus = ({ status }: { status: string }) => {
      setYjsConnected(status === "connected");
    };
    provider.on("status", onStatus);

    const messagesArr = doc.getArray<Record<string, unknown>>("messages");
    const pendingMap = doc.getMap<Record<string, unknown>>("pending");
    const votesMap = doc.getMap<"up" | "down">("votes");

    const syncMessages = () => {
      const out: MGrillMessage[] = [];
      messagesArr.forEach((raw) => {
        const m = coerceMessage(raw);
        if (m) out.push(m);
      });
      setMessages(out);
    };

    const syncPending = () => {
      const out: MGrillPendingEntry[] = [];
      pendingMap.forEach((raw, key) => {
        const p = coercePending(key, raw);
        if (p) out.push(p);
      });
      out.sort((a, b) => a.timestamp - b.timestamp);
      setPending(out);
    };

    const syncVotes = () => {
      const out: Record<string, "up" | "down"> = {};
      votesMap.forEach((v, key) => {
        if (v === "up" || v === "down") out[key] = v;
      });
      setVotes(out);
    };

    messagesArr.observe(syncMessages);
    pendingMap.observe(syncPending);
    votesMap.observe(syncVotes);
    syncMessages();
    syncPending();
    syncVotes();

    return () => {
      provider.off("status", onStatus);
      messagesArr.unobserve(syncMessages);
      pendingMap.unobserve(syncPending);
      votesMap.unobserve(syncVotes);
      provider.destroy();
      doc.destroy();
      providerRef.current = null;
      docRef.current = null;
    };
  }, [sessionId, tearDownYjs]);

  // Heartbeat while we are the creator.
  useEffect(() => {
    stopHeartbeat();
    if (!sessionId || !state?.can_act_as_creator) return;
    const beat = async () => {
      try {
        await fetch(apiUrl(`/mgrill/${sessionId}/heartbeat`), {
          method: "POST",
          headers: tokenHeaders(tokenRef.current),
          body: JSON.stringify({ player_id: state.creator_player_id ?? null }),
        });
      } catch {
        // ignore
      }
    };
    heartbeatRef.current = window.setInterval(
      () => void beat(),
      HEARTBEAT_INTERVAL_MS,
    );
    void beat();
    return stopHeartbeat;
  }, [sessionId, state?.can_act_as_creator, state?.creator_player_id, stopHeartbeat]);

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      stopPolling();
      stopHeartbeat();
      tearDownYjs();
    };
  }, [stopPolling, stopHeartbeat, tearDownYjs]);

  const createSession = useCallback(
    async (form: MGrillCreateForm, creatorName: string): Promise<string | null> => {
      setError(null);
      setIsLoading(true);
      try {
        const refRepos = form.reference_repos
          .split(",")
          .map((s) => s.trim())
          .filter((s) => s.length > 0);
        const res = await fetch(apiUrl("/mgrill/sessions"), {
          method: "POST",
          headers: tokenHeaders(tokenRef.current),
          body: JSON.stringify({
            repo_path: form.repo_path,
            prompt: form.prompt,
            model: form.model || null,
            reference_repos: refRepos,
            backend: form.backend || "claudecodecli",
            creator_name: creatorName,
          }),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          setError(
            (detail as { detail?: string }).detail ?? `HTTP ${res.status}`,
          );
          return null;
        }
        const data = (await res.json()) as MGrillCreateResponse;
        setSessionId(data.session_id);
        sessionIdRef.current = data.session_id;
        startPolling();
        return data.session_id;
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [startPolling],
  );

  const joinSession = useCallback(
    (sid: string) => {
      setError(null);
      setSessionId(sid);
      sessionIdRef.current = sid;
      setState(null);
      startPolling();
    },
    [startPolling],
  );

  const leaveSession = useCallback(() => {
    stopPolling();
    stopHeartbeat();
    tearDownYjs();
    setSessionId(null);
    sessionIdRef.current = null;
    setState(null);
    setError(null);
  }, [stopPolling, stopHeartbeat, tearDownYjs]);

  const addPending = useCallback(
    async (content: string, playerId: string, playerName: string) => {
      const sid = sessionIdRef.current;
      if (!sid) return;
      try {
        const res = await fetch(apiUrl(`/mgrill/${sid}/pending`), {
          method: "POST",
          headers: tokenHeaders(tokenRef.current),
          body: JSON.stringify({ player_id: playerId, name: playerName, content }),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          setError((detail as { detail?: string }).detail ?? `Add pending failed: HTTP ${res.status}`);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [],
  );

  const removePending = useCallback(
    async (pendingId: string, playerId: string) => {
      const sid = sessionIdRef.current;
      if (!sid) return;
      try {
        const res = await fetch(apiUrl(`/mgrill/${sid}/pending/${pendingId}`), {
          method: "DELETE",
          headers: tokenHeaders(tokenRef.current, { "X-MGrill-Player-Id": playerId }),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          setError((detail as { detail?: string }).detail ?? `Remove pending failed: HTTP ${res.status}`);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [],
  );

  const sendToAi = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;
    try {
      const res = await fetch(apiUrl(`/mgrill/${sid}/send`), {
        method: "POST",
        headers: tokenHeaders(tokenRef.current),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        setError((detail as { detail?: string }).detail ?? `HTTP ${res.status}`);
      }
      void pollState();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [pollState]);

  const requestPlan = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;
    try {
      const res = await fetch(apiUrl(`/mgrill/${sid}/request-plan`), {
        method: "POST",
        headers: tokenHeaders(tokenRef.current),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        setError((detail as { detail?: string }).detail ?? `Request plan failed: HTTP ${res.status}`);
      }
      void pollState();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [pollState]);

  const castVote = useCallback(
    async (playerId: string, vote: "up" | "down" | "clear") => {
      const sid = sessionIdRef.current;
      if (!sid) return;
      try {
        const res = await fetch(apiUrl(`/mgrill/${sid}/vote`), {
          method: "POST",
          headers: tokenHeaders(tokenRef.current),
          body: JSON.stringify({ player_id: playerId, vote }),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          setError((detail as { detail?: string }).detail ?? `Vote failed: HTTP ${res.status}`);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [],
  );

  const submitPlan = useCallback(
    async (opts?: { override?: boolean }) => {
      const sid = sessionIdRef.current;
      if (!sid) return { ok: false as const, status: 0, body: null };
      const override = opts?.override ? "?override=true" : "";
      try {
        const res = await fetch(apiUrl(`/mgrill/${sid}/submit${override}`), {
          method: "POST",
          headers: tokenHeaders(tokenRef.current),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          return { ok: false as const, status: res.status, body };
        }
        const data = (await res.json()) as {
          task_id: string;
          override: boolean;
        };
        void pollState();
        return { ok: true as const, task_id: data.task_id, override: data.override };
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        return { ok: false as const, status: 0, body: null };
      }
    },
    [pollState],
  );

  const keepGrilling = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;
    try {
      const res = await fetch(apiUrl(`/mgrill/${sid}/keep-grilling`), {
        method: "POST",
        headers: tokenHeaders(tokenRef.current),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        setError((detail as { detail?: string }).detail ?? `Keep grilling failed: HTTP ${res.status}`);
      }
      void pollState();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [pollState]);

  const claimCreator = useCallback(
    async (playerId: string, playerName: string) => {
      const sid = sessionIdRef.current;
      if (!sid) return { ok: false as const, status: 0, body: null };
      try {
        const res = await fetch(apiUrl(`/mgrill/${sid}/claim-creator`), {
          method: "POST",
          headers: tokenHeaders(tokenRef.current, { "X-MGrill-Player-Name": playerName }),
          body: JSON.stringify({ player_id: playerId }),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          return { ok: false as const, status: res.status, body };
        }
        void pollState();
        return { ok: true as const };
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        return { ok: false as const, status: 0, body: null };
      }
    },
    [pollState],
  );

  // Derive final_plan from the transcript (most recent ``type == "plan"``).
  const finalPlan = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].type === "plan") {
        return messages[i].content;
      }
    }
    return null;
  }, [messages]);

  const live: MGrillSessionLiveState = {
    messages,
    pending,
    votes,
    finalPlan,
    yjsConnected,
  };

  return {
    state,
    live,
    sessionId,
    error,
    isLoading,
    createSession,
    joinSession,
    leaveSession,
    addPending,
    removePending,
    sendToAi,
    requestPlan,
    castVote,
    submitPlan,
    keepGrilling,
    claimCreator,
  };
}

// ---------------------------------------------------------------------------
// Lobby hook
// ---------------------------------------------------------------------------

export type MGrillLobbyState = {
  sessions: MGrillSessionSummary[];
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
};

export function useMultiplayerGrillLobby(active: boolean): MGrillLobbyState {
  const [sessions, setSessions] = useState<MGrillSessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetch(apiUrl(`/mgrill/sessions?_=${Date.now()}`), {
        cache: "no-store",
      });
      if (!res.ok) {
        if (res.status !== 404) {
          setError(`HTTP ${res.status}`);
        }
        return;
      }
      const data = (await res.json()) as MGrillListResponse;
      setSessions(data.sessions);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!active) {
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }
    void load();
    timerRef.current = window.setInterval(() => void load(), LOBBY_POLL_INTERVAL_MS);
    return () => {
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [active, load]);

  return { sessions, isLoading, error, refresh: load };
}
