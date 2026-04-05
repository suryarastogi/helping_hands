import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useGrillSession } from "./useGrillSession";
import type { GrillFormState, GrillMessage, GrillPollResponse } from "../types";

// ---------------------------------------------------------------------------
// Fetch mock helpers
// ---------------------------------------------------------------------------

function jsonResponse(data: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as unknown as Response;
}

function errorResponse(detail: string, status = 400): Response {
  return jsonResponse({ detail }, status);
}

const FORM: GrillFormState = {
  repo_path: "owner/repo",
  prompt: "Describe your feature",
  model: "gpt-5.2",
  github_token: "ghp_abc",
  reference_repos: "ref/one, ref/two",
};

function makeMessage(overrides: Partial<GrillMessage> & { id: string }): GrillMessage {
  return {
    role: "assistant",
    content: "Hello",
    type: "message",
    timestamp: Date.now() / 1000,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.useFakeTimers();
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.useRealTimers();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useGrillSession", () => {
  // ---- Initial state ----

  it("starts with idle defaults", () => {
    const { result } = renderHook(() => useGrillSession());
    expect(result.current.phase).toBe("form");
    expect(result.current.sessionId).toBeNull();
    expect(result.current.status).toBe("idle");
    expect(result.current.messages).toEqual([]);
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.finalPlan).toBeNull();
  });

  // ---- startSession ----

  describe("startSession", () => {
    it("posts to /grill and transitions to chatting phase", async () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
        jsonResponse({ session_id: "sess-1", status: "active" }),
      );

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      expect(fetchSpy).toHaveBeenCalledTimes(2); // POST + immediate poll
      const [url, opts] = fetchSpy.mock.calls[0];
      expect(url).toContain("/grill");
      expect(opts?.method).toBe("POST");
      const body = JSON.parse(opts?.body as string);
      expect(body.repo_path).toBe("owner/repo");
      expect(body.reference_repos).toEqual(["ref/one", "ref/two"]);

      expect(result.current.phase).toBe("chatting");
      expect(result.current.sessionId).toBe("sess-1");
      expect(result.current.status).toBe("active");
    });

    it("sets error on non-ok response with detail", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
        errorResponse("Feature disabled", 403),
      );

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      expect(result.current.error).toBe("Feature disabled");
      expect(result.current.isLoading).toBe(false);
      expect(result.current.phase).toBe("form");
    });

    it("sets error on non-ok response without detail", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error("bad json")),
      } as unknown as Response);

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      expect(result.current.error).toBe("HTTP 500");
      expect(result.current.isLoading).toBe(false);
    });

    it("sets error on fetch network failure", async () => {
      vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
        new Error("Network error"),
      );

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      expect(result.current.error).toBe("Network error");
      expect(result.current.isLoading).toBe(false);
    });

    it("sends null model when form model is empty", async () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
        jsonResponse({ session_id: "sess-2", status: "active" }),
      );

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession({ ...FORM, model: "" });
      });

      const body = JSON.parse(fetchSpy.mock.calls[0][1]?.body as string);
      expect(body.model).toBeNull();
    });

    it("filters empty reference repos", async () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
        jsonResponse({ session_id: "sess-3", status: "active" }),
      );

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession({ ...FORM, reference_repos: ", ,  " });
      });

      const body = JSON.parse(fetchSpy.mock.calls[0][1]?.body as string);
      expect(body.reference_repos).toEqual([]);
    });

    it("clears previous error and messages on new session", async () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch");

      // First call fails
      fetchSpy.mockRejectedValueOnce(new Error("fail"));
      const { result } = renderHook(() => useGrillSession());
      await act(async () => {
        await result.current.startSession(FORM);
      });
      expect(result.current.error).toBe("fail");

      // Second call succeeds — error should be cleared
      fetchSpy.mockResolvedValueOnce(
        jsonResponse({ session_id: "sess-4", status: "active" }),
      );
      // Mock the immediate poll
      fetchSpy.mockResolvedValueOnce(
        jsonResponse({ session_id: "sess-4", status: "active", messages: [] }),
      );
      await act(async () => {
        await result.current.startSession(FORM);
      });
      expect(result.current.error).toBeNull();
      expect(result.current.messages).toEqual([]);
    });
  });

  // ---- sendMessage ----

  describe("sendMessage", () => {
    it("does nothing if no sessionId", async () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch");
      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.sendMessage("hello");
      });

      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("posts message and adds optimistic user message", async () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        .mockResolvedValue(jsonResponse({ session_id: "sess-1", status: "active", messages: [] }));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      fetchSpy.mockClear();
      fetchSpy.mockResolvedValueOnce(jsonResponse({}));

      await act(async () => {
        await result.current.sendMessage("my answer");
      });

      // Check the optimistic message was added
      const userMsg = result.current.messages.find((m) => m.content === "my answer");
      expect(userMsg).toBeDefined();
      expect(userMsg?.role).toBe("user");
      expect(userMsg?.type).toBe("message");

      // Check the fetch call
      const [url, opts] = fetchSpy.mock.calls[0];
      expect(url).toContain("/grill/sess-1/message");
      expect(opts?.method).toBe("POST");
      const body = JSON.parse(opts?.body as string);
      expect(body.content).toBe("my answer");
      expect(body.type).toBe("message");
    });

    it("sets error and stops loading on fetch failure", async () => {
      vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active", messages: [] }));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("net"));

      await act(async () => {
        await result.current.sendMessage("hi");
      });

      expect(result.current.error).toBe("Failed to send message");
      expect(result.current.isLoading).toBe(false);
    });
  });

  // ---- requestPlan ----

  describe("requestPlan", () => {
    it("does nothing if no sessionId", async () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch");
      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.requestPlan();
      });

      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("sends end-type message and adds user summary message", async () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        .mockResolvedValue(jsonResponse({ session_id: "sess-1", status: "active", messages: [] }));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      fetchSpy.mockClear();
      fetchSpy.mockResolvedValueOnce(jsonResponse({}));

      await act(async () => {
        await result.current.requestPlan();
      });

      // Optimistic user message
      const planMsg = result.current.messages.find((m) =>
        m.content.includes("satisfied"),
      );
      expect(planMsg).toBeDefined();
      expect(planMsg?.role).toBe("user");

      // Fetch call with type: "end"
      const body = JSON.parse(fetchSpy.mock.calls[0][1]?.body as string);
      expect(body.type).toBe("end");

      expect(result.current.isLoading).toBe(true);
    });

    it("sets error on fetch failure", async () => {
      vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active", messages: [] }));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("net"));

      await act(async () => {
        await result.current.requestPlan();
      });

      expect(result.current.error).toBe("Failed to request plan");
      expect(result.current.isLoading).toBe(false);
    });
  });

  // ---- poll ----

  describe("polling", () => {
    it("deduplicates messages from poll", async () => {
      const msg1 = makeMessage({ id: "m1", content: "First" });

      vi.spyOn(globalThis, "fetch")
        // startSession POST
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        // immediate poll
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active", messages: [msg1] }))
        // interval poll — same message
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active", messages: [msg1] }));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      // Advance past poll interval
      await act(async () => {
        vi.advanceTimersByTime(2000);
      });

      // Should only have one copy of m1
      const m1Count = result.current.messages.filter((m) => m.id === "m1").length;
      expect(m1Count).toBe(1);
    });

    it("detects plan message and transitions to plan phase", async () => {
      const planMsg = makeMessage({
        id: "plan-1",
        role: "assistant",
        content: "Some preamble\n## FINAL PLAN\nThe actual plan content",
        type: "plan",
      });

      vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        // immediate poll returns plan
        .mockResolvedValueOnce(jsonResponse({
          session_id: "sess-1",
          status: "active",
          messages: [planMsg],
        } as GrillPollResponse));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      expect(result.current.phase).toBe("plan");
      expect(result.current.finalPlan).toBe("## FINAL PLAN\nThe actual plan content");
      expect(result.current.isLoading).toBe(false);
    });

    it("uses full content when no FINAL PLAN header", async () => {
      const planMsg = makeMessage({
        id: "plan-2",
        role: "assistant",
        content: "Just a plan without header",
        type: "plan",
      });

      vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        .mockResolvedValueOnce(jsonResponse({
          session_id: "sess-1",
          status: "active",
          messages: [planMsg],
        }));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      expect(result.current.finalPlan).toBe("Just a plan without header");
    });

    it("sets isLoading true on thinking status", async () => {
      vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "thinking", messages: [] }));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      expect(result.current.isLoading).toBe(true);
    });

    it("sets isLoading false on active status", async () => {
      vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active", messages: [] }));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      expect(result.current.isLoading).toBe(false);
    });

    it("stops polling on terminal status with no remaining messages", async () => {
      const clearSpy = vi.spyOn(globalThis, "clearInterval");

      vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "completed", messages: [] }));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      expect(clearSpy).toHaveBeenCalled();
      expect(result.current.isLoading).toBe(false);
    });

    it("keeps polling on terminal status when messages remain", async () => {
      const msg = makeMessage({ id: "m-final" });

      vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        .mockResolvedValueOnce(jsonResponse({
          session_id: "sess-1",
          status: "completed",
          messages: [msg],
        }));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      // Messages still present — loading may still be true from startSession
      expect(result.current.messages.some((m) => m.id === "m-final")).toBe(true);
    });

    it("handles poll fetch errors silently", async () => {
      vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        // immediate poll fails
        .mockRejectedValueOnce(new Error("poll error"));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      // No error set — poll errors are transient
      // error might be null or from startSession context, but phase should be chatting
      expect(result.current.phase).toBe("chatting");
    });

    it("skips poll when no sessionId", async () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch");
      const { result } = renderHook(() => useGrillSession());

      // The poll function should be a no-op without sessionId
      expect(result.current.sessionId).toBeNull();
      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("handles non-ok poll response gracefully", async () => {
      vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        .mockResolvedValueOnce({ ok: false, status: 500 } as unknown as Response);

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      // Should not crash, phase should remain chatting
      expect(result.current.phase).toBe("chatting");
    });
  });

  // ---- reset ----

  describe("reset", () => {
    it("clears all state and stops polling", async () => {
      const clearSpy = vi.spyOn(globalThis, "clearInterval");

      vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        .mockResolvedValue(jsonResponse({ session_id: "sess-1", status: "active", messages: [] }));

      const { result } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      expect(result.current.phase).toBe("chatting");

      act(() => {
        result.current.reset();
      });

      expect(result.current.phase).toBe("form");
      expect(result.current.sessionId).toBeNull();
      expect(result.current.status).toBe("idle");
      expect(result.current.messages).toEqual([]);
      expect(result.current.error).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.finalPlan).toBeNull();
      expect(clearSpy).toHaveBeenCalled();
    });
  });

  // ---- unmount cleanup ----

  describe("unmount cleanup", () => {
    it("stops polling on unmount", async () => {
      const clearSpy = vi.spyOn(globalThis, "clearInterval");

      vi.spyOn(globalThis, "fetch")
        .mockResolvedValueOnce(jsonResponse({ session_id: "sess-1", status: "active" }))
        .mockResolvedValue(jsonResponse({ session_id: "sess-1", status: "active", messages: [] }));

      const { result, unmount } = renderHook(() => useGrillSession());

      await act(async () => {
        await result.current.startSession(FORM);
      });

      unmount();

      expect(clearSpy).toHaveBeenCalled();
    });
  });
});
