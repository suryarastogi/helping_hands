import { useCallback, useEffect, useRef, useState } from "react";

import { apiUrl, saveGithubToken } from "../App.utils";
import { computeBackoffDelay } from "./pollingBackoff";
import type {
  GrillFormState,
  GrillMessage,
  GrillPhase,
  GrillPollResponse,
  GrillResumableListResponse,
  GrillSessionSummary,
  GrillStartResponse,
} from "../types";

const POLL_INTERVAL_MS = 1500;
const POLL_MAX_INTERVAL_MS = 10_000;
/** Consecutive poll failures before surfacing an error to the user. */
const POLL_FAILURE_NOTIFY_THRESHOLD = 5;
const PERSISTED_SESSION_KEY = "hh_grill_active_session";
const PERSISTED_SESSION_MAX_AGE_MS = 60 * 60 * 1000; // 1 hour

// ---------------------------------------------------------------------------
// localStorage persistence for the active grill session
// ---------------------------------------------------------------------------

export type PersistedGrillSession = {
  sessionId: string;
  prompt: string;
  repoPath: string;
  startedAt: number;
};

export function savePersistedGrillSession(data: PersistedGrillSession): void {
  try {
    localStorage.setItem(PERSISTED_SESSION_KEY, JSON.stringify(data));
  } catch {
    /* quota exceeded or unavailable */
  }
}

export function loadPersistedGrillSession(): PersistedGrillSession | null {
  try {
    const raw = localStorage.getItem(PERSISTED_SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      typeof parsed.sessionId !== "string" ||
      typeof parsed.startedAt !== "number"
    ) {
      return null;
    }
    if (Date.now() - parsed.startedAt > PERSISTED_SESSION_MAX_AGE_MS) {
      localStorage.removeItem(PERSISTED_SESSION_KEY);
      return null;
    }
    return parsed as PersistedGrillSession;
  } catch {
    return null;
  }
}

export function clearPersistedGrillSession(): void {
  try {
    localStorage.removeItem(PERSISTED_SESSION_KEY);
  } catch {
    /* ignore */
  }
}

export type GrillSessionState = {
  phase: GrillPhase;
  sessionId: string | null;
  status: string;
  messages: GrillMessage[];
  error: string | null;
  isLoading: boolean;
  finalPlan: string | null;

  startSession: (form: GrillFormState) => Promise<void>;
  resumeSession: (sessionId: string) => void;
  sendMessage: (content: string) => Promise<void>;
  requestPlan: () => Promise<void>;
  reset: () => void;
  suspend: () => void;
  wake: () => void;
};

export function useGrillSession(): GrillSessionState {
  const [phase, setPhase] = useState<GrillPhase>("form");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState("idle");
  const [messages, setMessages] = useState<GrillMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [finalPlan, setFinalPlan] = useState<string | null>(null);
  const pollingRef = useRef<number | null>(null);
  const pollingActiveRef = useRef(false);
  const sessionIdRef = useRef<string | null>(null);
  /** Consecutive poll failures — drives exponential backoff. */
  const pollFailuresRef = useRef(0);
  /** Whether the current `error` value was set by the poll-failure path. */
  const pollErrorNotifiedRef = useRef(false);

  // Keep ref in sync
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  const stopPolling = useCallback(() => {
    pollingActiveRef.current = false;
    if (pollingRef.current !== null) {
      window.clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  /** Single poll attempt. Returns false on a failed request. */
  const poll = useCallback(async (): Promise<boolean> => {
    const sid = sessionIdRef.current;
    if (!sid) return true;

    try {
      const res = await fetch(apiUrl(`/grill/${sid}?_=${Date.now()}`), {
        cache: "no-store",
      });
      if (!res.ok) return false;
      const data = (await res.json()) as GrillPollResponse;

      setStatus(data.status);

      if (data.messages.length > 0) {
        setMessages((prev) => {
          const existingIds = new Set(prev.map((m) => m.id));
          const newMsgs = data.messages.filter((m) => !existingIds.has(m.id));
          return [...prev, ...newMsgs];
        });

        // Check for final plan
        for (const msg of data.messages) {
          if (msg.type === "plan") {
            const planContent = msg.content;
            // Extract everything after "## FINAL PLAN"
            const planIdx = planContent.indexOf("## FINAL PLAN");
            setFinalPlan(
              planIdx >= 0 ? planContent.slice(planIdx) : planContent,
            );
            setPhase("plan");
            setIsLoading(false);
          }
        }
      }

      // Stop polling on terminal states
      if (
        data.status === "completed" ||
        data.status === "error" ||
        data.status === "max_turns" ||
        data.status === "not_found"
      ) {
        clearPersistedGrillSession();
        // Keep polling briefly to drain remaining messages, then stop
        if (data.messages.length === 0) {
          stopPolling();
          setIsLoading(false);
          if (data.status === "not_found") {
            setPhase("form");
            setSessionId(null);
            setStatus("idle");
          }
        }
      }

      // When AI is thinking, show loading; suspended sessions are idle
      if (data.status === "thinking") {
        setIsLoading(true);
      } else if (data.status === "active" || data.status === "suspended") {
        setIsLoading(false);
      }
      return true;
    } catch {
      // Transient fetch error — keep polling (with backoff)
      return false;
    }
  }, [stopPolling]);

  const runPollLoop = useCallback(async () => {
    if (!pollingActiveRef.current) return;
    const ok = await poll();
    if (ok) {
      pollFailuresRef.current = 0;
      if (pollErrorNotifiedRef.current) {
        pollErrorNotifiedRef.current = false;
        setError(null);
      }
    } else {
      pollFailuresRef.current += 1;
      if (
        pollFailuresRef.current === POLL_FAILURE_NOTIFY_THRESHOLD &&
        !pollErrorNotifiedRef.current
      ) {
        pollErrorNotifiedRef.current = true;
        setError("Connection to grill session lost — retrying…");
      }
    }
    if (!pollingActiveRef.current) return;
    pollingRef.current = window.setTimeout(
      () => void runPollLoop(),
      computeBackoffDelay(POLL_INTERVAL_MS, pollFailuresRef.current, POLL_MAX_INTERVAL_MS),
    );
  }, [poll]);

  const startPolling = useCallback(() => {
    stopPolling();
    pollingActiveRef.current = true;
    pollFailuresRef.current = 0;
    // Immediate poll, then self-rescheduling loop with failure backoff.
    void runPollLoop();
  }, [runPollLoop, stopPolling]);

  // Cleanup on unmount
  useEffect(() => stopPolling, [stopPolling]);

  const startSession = useCallback(
    async (form: GrillFormState) => {
      setError(null);
      setIsLoading(true);
      setMessages([]);
      setFinalPlan(null);

      const refRepos = form.reference_repos
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);

      if (form.github_token?.trim()) {
        saveGithubToken(form.github_token);
      }

      try {
        const res = await fetch(apiUrl("/grill"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            repo_path: form.repo_path,
            prompt: form.prompt,
            model: form.model || null,
            github_token: form.github_token || null,
            reference_repos: refRepos,
            backend: form.backend || "claudecodecli",
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          const detail = (errData as { detail?: string }).detail ?? `HTTP ${res.status}`;
          setError(detail);
          setIsLoading(false);
          return;
        }

        const data = (await res.json()) as GrillStartResponse;
        setSessionId(data.session_id);
        setStatus(data.status);
        setPhase("chatting");

        // Start polling after a short delay to let the task begin
        sessionIdRef.current = data.session_id;
        savePersistedGrillSession({
          sessionId: data.session_id,
          prompt: form.prompt,
          repoPath: form.repo_path,
          startedAt: Date.now(),
        });
        startPolling();
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setIsLoading(false);
      }
    },
    [startPolling],
  );

  const resumeSession = useCallback(
    (sid: string) => {
      setError(null);
      setMessages([]);
      setFinalPlan(null);
      setSessionId(sid);
      sessionIdRef.current = sid;
      setStatus("suspended");
      setPhase("chatting");
      setIsLoading(false);

      savePersistedGrillSession({
        sessionId: sid,
        prompt: "",
        repoPath: "",
        startedAt: Date.now(),
      });

      // Fetch the full transcript before polling: the poll endpoint drains
      // the AI queue destructively, so without this the chat view stays
      // empty after resume. Errors fall through to polling — better to
      // start with no history than no chat at all.
      void (async () => {
        try {
          const res = await fetch(apiUrl(`/grill/${sid}/transcript?_=${Date.now()}`), {
            cache: "no-store",
          });
          if (res.ok) {
            const data = (await res.json()) as GrillPollResponse;
            if (sessionIdRef.current !== sid) return;
            setStatus(data.status);
            if (data.messages.length > 0) {
              setMessages((prev) => {
                const existingIds = new Set(prev.map((m) => m.id));
                const newMsgs = data.messages.filter((m) => !existingIds.has(m.id));
                return [...prev, ...newMsgs];
              });
              for (const msg of data.messages) {
                if (msg.type === "plan") {
                  const planContent = msg.content;
                  const planIdx = planContent.indexOf("## FINAL PLAN");
                  setFinalPlan(
                    planIdx >= 0 ? planContent.slice(planIdx) : planContent,
                  );
                  setPhase("plan");
                }
              }
            }
          }
        } catch {
          // Transient — polling will still run.
        }
        startPolling();
      })();
    },
    [startPolling],
  );

  const sendMessage = useCallback(
    async (content: string) => {
      if (!sessionId) return;
      setIsLoading(true);

      // Optimistically add user message to the list
      const userMsg: GrillMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
        type: "message",
        timestamp: Date.now() / 1000,
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        await fetch(apiUrl(`/grill/${sessionId}/message`), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content, type: "message" }),
        });
      } catch {
        setError("Failed to send message");
        setIsLoading(false);
      }
    },
    [sessionId],
  );

  const requestPlan = useCallback(async () => {
    if (!sessionId) return;
    setIsLoading(true);

    const userMsg: GrillMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: "I'm satisfied with the discussion. Please produce the final plan.",
      type: "message",
      timestamp: Date.now() / 1000,
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      await fetch(apiUrl(`/grill/${sessionId}/message`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: "I'm satisfied with the discussion. Please produce the final plan.",
          type: "end",
        }),
      });
    } catch {
      setError("Failed to request plan");
      setIsLoading(false);
    }
  }, [sessionId]);

  const reset = useCallback(() => {
    stopPolling();
    clearPersistedGrillSession();
    setPhase("form");
    setSessionId(null);
    setStatus("idle");
    setMessages([]);
    setError(null);
    setIsLoading(false);
    setFinalPlan(null);
  }, [stopPolling]);

  const suspend = useCallback(() => {
    stopPolling();
  }, [stopPolling]);

  const wake = useCallback(() => {
    if (sessionIdRef.current) {
      startPolling();
    }
  }, [startPolling]);

  return {
    phase,
    sessionId,
    status,
    messages,
    error,
    isLoading,
    finalPlan,
    startSession,
    resumeSession,
    sendMessage,
    requestPlan,
    reset,
    suspend,
    wake,
  };
}

export type ResumableSessionsState = {
  sessions: GrillSessionSummary[];
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
};

export function useResumableGrillSessions(active: boolean): ResumableSessionsState {
  const [sessions, setSessions] = useState<GrillSessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetch(apiUrl(`/grill/sessions/resumable?_=${Date.now()}`), {
        cache: "no-store",
      });
      if (!res.ok) {
        if (res.status !== 404) {
          setError(`HTTP ${res.status}`);
        }
        return;
      }
      const data = (await res.json()) as GrillResumableListResponse;
      setSessions(data.sessions);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!active) return;
    void load();
  }, [active, load]);

  return { sessions, isLoading, error, refresh: load };
}
