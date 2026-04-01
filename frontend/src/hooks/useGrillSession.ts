import { useCallback, useEffect, useRef, useState } from "react";

import { apiUrl } from "../App.utils";
import type {
  GrillFormState,
  GrillMessage,
  GrillPhase,
  GrillPollResponse,
  GrillStartResponse,
} from "../types";

const POLL_INTERVAL_MS = 1500;

export type GrillSessionState = {
  phase: GrillPhase;
  sessionId: string | null;
  status: string;
  messages: GrillMessage[];
  error: string | null;
  isLoading: boolean;
  finalPlan: string | null;

  startSession: (form: GrillFormState) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  requestPlan: () => Promise<void>;
  reset: () => void;
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
  const sessionIdRef = useRef<string | null>(null);

  // Keep ref in sync
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  const stopPolling = useCallback(() => {
    if (pollingRef.current !== null) {
      window.clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const poll = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;

    try {
      const res = await fetch(apiUrl(`/grill/${sid}?_=${Date.now()}`), {
        cache: "no-store",
      });
      if (!res.ok) return;
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
        data.status === "timeout" ||
        data.status === "max_turns" ||
        data.status === "not_found"
      ) {
        // Keep polling briefly to drain remaining messages, then stop
        if (data.messages.length === 0) {
          stopPolling();
          setIsLoading(false);
        }
      }

      // When AI is thinking, show loading
      if (data.status === "thinking") {
        setIsLoading(true);
      } else if (data.status === "active") {
        setIsLoading(false);
      }
    } catch {
      // Transient fetch error — keep polling
    }
  }, [stopPolling]);

  const startPolling = useCallback(() => {
    stopPolling();
    pollingRef.current = window.setInterval(() => void poll(), POLL_INTERVAL_MS);
    // Also do an immediate poll
    void poll();
  }, [poll, stopPolling]);

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
        startPolling();
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setIsLoading(false);
      }
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
    setPhase("form");
    setSessionId(null);
    setStatus("idle");
    setMessages([]);
    setError(null);
    setIsLoading(false);
    setFinalPlan(null);
  }, [stopPolling]);

  return {
    phase,
    sessionId,
    status,
    messages,
    error,
    isLoading,
    finalPlan,
    startSession,
    sendMessage,
    requestPlan,
    reset,
  };
}
