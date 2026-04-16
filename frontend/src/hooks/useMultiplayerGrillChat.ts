/**
 * useMultiplayerGrillChat — non-draining message poller for a shared grill
 * session. Multiple clients can poll the same session because the backend
 * exposes the full message history at ``/grill/{id}/history``.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { apiUrl } from "../App.utils";
import type { GrillMessage, GrillPollResponse } from "../types";

const POLL_INTERVAL_MS = 1500;

export type MultiplayerGrillChatState = {
  messages: GrillMessage[];
  status: string;
  finalPlan: string | null;
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  requestPlan: () => Promise<void>;
  endSession: () => Promise<void>;
};

export function useMultiplayerGrillChat(
  sessionId: string | null,
): MultiplayerGrillChatState {
  const [messages, setMessages] = useState<GrillMessage[]>([]);
  const [status, setStatus] = useState<string>("idle");
  const [finalPlan, setFinalPlan] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);
  const lastIdsRef = useRef<Set<string>>(new Set());

  // Reset state when the session changes.
  useEffect(() => {
    setMessages([]);
    setStatus(sessionId ? "connecting" : "idle");
    setFinalPlan(null);
    setIsLoading(false);
    setError(null);
    lastIdsRef.current = new Set();
  }, [sessionId]);

  // Polling loop — uses the non-draining /grill/{id}/history endpoint so
  // multiple clients can read the same session concurrently.
  useEffect(() => {
    if (!sessionId) return;

    let cancelled = false;
    const poll = async () => {
      try {
        const res = await fetch(
          apiUrl(`/grill/${sessionId}/history?_=${Date.now()}`),
          { cache: "no-store" },
        );
        if (!res.ok || cancelled) return;
        const data = (await res.json()) as GrillPollResponse;
        if (cancelled) return;

        setStatus(data.status);

        if (data.messages.length > 0) {
          // Replace the message list — the backend returns full history.
          // Track ids so we don't reset when nothing changed.
          const newIds = new Set(data.messages.map((m) => m.id));
          let changed = newIds.size !== lastIdsRef.current.size;
          if (!changed) {
            for (const id of newIds) {
              if (!lastIdsRef.current.has(id)) {
                changed = true;
                break;
              }
            }
          }
          if (changed) {
            lastIdsRef.current = newIds;
            setMessages(data.messages);
            for (const msg of data.messages) {
              if (msg.type === "plan") {
                const idx = msg.content.indexOf("## FINAL PLAN");
                setFinalPlan(idx >= 0 ? msg.content.slice(idx) : msg.content);
              }
            }
          }
        }

        if (data.status === "thinking") {
          setIsLoading(true);
        } else if (
          data.status === "active" ||
          data.status === "plan_ready"
        ) {
          setIsLoading(false);
        }
      } catch {
        // transient — keep polling
      }
    };

    void poll();
    pollRef.current = window.setInterval(() => void poll(), POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      if (pollRef.current !== null) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [sessionId]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!sessionId) return;
      setIsLoading(true);
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
    const text = "I'm satisfied with the discussion. Please produce the final plan.";
    try {
      await fetch(apiUrl(`/grill/${sessionId}/message`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: text, type: "end" }),
      });
    } catch {
      setError("Failed to request plan");
      setIsLoading(false);
    }
  }, [sessionId]);

  const endSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      await fetch(apiUrl(`/grill/${sessionId}/end`), { method: "POST" });
    } catch {
      // best-effort
    }
  }, [sessionId]);

  return {
    messages,
    status,
    finalPlan,
    isLoading,
    error,
    sendMessage,
    requestPlan,
    endSession,
  };
}
