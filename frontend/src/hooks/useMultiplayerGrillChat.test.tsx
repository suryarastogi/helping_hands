import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useMultiplayerGrillChat } from "./useMultiplayerGrillChat";
import type { GrillMessage } from "../types";

function jsonResponse(data: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as unknown as Response;
}

function makeMessage(overrides: Partial<GrillMessage> & { id: string }): GrillMessage {
  return {
    role: "assistant",
    content: "Hi",
    type: "message",
    timestamp: Date.now() / 1000,
    ...overrides,
  };
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useMultiplayerGrillChat", () => {
  it("returns idle defaults with no sessionId", () => {
    const { result } = renderHook(() => useMultiplayerGrillChat(null));
    expect(result.current.messages).toEqual([]);
    expect(result.current.status).toBe("idle");
    expect(result.current.finalPlan).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("polls /grill/{id}/history when sessionId is set", async () => {
    const msg = makeMessage({ id: "m-1", content: "hello" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ session_id: "abc", status: "active", messages: [msg] }),
    );

    const { result } = renderHook(() => useMultiplayerGrillChat("abc"));

    await act(async () => {
      await Promise.resolve();
    });

    expect(fetchSpy).toHaveBeenCalled();
    const url = String(fetchSpy.mock.calls[0][0]);
    expect(url).toContain("/grill/abc/history");
    expect(result.current.messages.some((m) => m.id === "m-1")).toBe(true);
    expect(result.current.status).toBe("active");
  });

  it("extracts FINAL PLAN content from plan-typed messages", async () => {
    const planMsg = makeMessage({
      id: "p-1",
      type: "plan",
      content: "preamble\n\n## FINAL PLAN\n\nDo this thing",
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ session_id: "abc", status: "plan_ready", messages: [planMsg] }),
    );

    const { result } = renderHook(() => useMultiplayerGrillChat("abc"));

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.finalPlan).toContain("## FINAL PLAN");
    expect(result.current.finalPlan).toContain("Do this thing");
  });

  it("resets state when sessionId changes", async () => {
    const msg = makeMessage({ id: "m-1" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ session_id: "abc", status: "active", messages: [msg] }),
    );

    const { result, rerender } = renderHook(
      ({ id }: { id: string | null }) => useMultiplayerGrillChat(id),
      { initialProps: { id: "abc" as string | null } },
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.messages.length).toBeGreaterThan(0);

    rerender({ id: null });

    expect(result.current.messages).toEqual([]);
    expect(result.current.status).toBe("idle");
  });

  it("posts to /grill/{id}/message on sendMessage", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValue(
        jsonResponse({ session_id: "abc", status: "active", messages: [] }),
      );

    const { result } = renderHook(() => useMultiplayerGrillChat("abc"));

    await act(async () => {
      await result.current.sendMessage("a question");
    });

    const postCall = fetchSpy.mock.calls.find((c) =>
      String(c[0]).includes("/grill/abc/message"),
    );
    expect(postCall).toBeDefined();
    expect((postCall![1] as { method?: string }).method).toBe("POST");
    const body = JSON.parse((postCall![1] as { body: string }).body);
    expect(body.content).toBe("a question");
    expect(body.type).toBe("message");
  });

  it("posts end-type message on requestPlan", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValue(
        jsonResponse({ session_id: "abc", status: "active", messages: [] }),
      );

    const { result } = renderHook(() => useMultiplayerGrillChat("abc"));

    await act(async () => {
      await result.current.requestPlan();
    });

    const postCall = fetchSpy.mock.calls.find(
      (c) =>
        String(c[0]).includes("/grill/abc/message") &&
        ((c[1] as { body?: string })?.body ?? "").includes('"end"'),
    );
    expect(postCall).toBeDefined();
  });

  it("posts to /grill/{id}/end on endSession", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValue(
        jsonResponse({ session_id: "abc", status: "active", messages: [] }),
      );

    const { result } = renderHook(() => useMultiplayerGrillChat("abc"));

    await act(async () => {
      await result.current.endSession();
    });

    const endCall = fetchSpy.mock.calls.find((c) =>
      String(c[0]).includes("/grill/abc/end"),
    );
    expect(endCall).toBeDefined();
    expect((endCall![1] as { method?: string }).method).toBe("POST");
  });
});
