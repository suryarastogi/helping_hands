import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, cleanup } from "@testing-library/react";

import { useTaskManager } from "./useTaskManager";
import { TASK_HISTORY_STORAGE_KEY } from "../App.utils";

// ---------------------------------------------------------------------------
// Fetch mock helpers
// ---------------------------------------------------------------------------

function jsonResponse(data: unknown, status = 200): Response {
  const body = typeof data === "string" ? data : JSON.stringify(data);
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(typeof data === "string" ? JSON.parse(data) : data),
    text: () => Promise.resolve(body),
    clone() { return jsonResponse(data, status); },
  } as unknown as Response;
}

function errorResponse(detail: string, status = 400): Response {
  return jsonResponse({ detail }, status);
}

/** Default mock that handles all polling endpoints gracefully. */
function defaultFetchMock(input: RequestInfo | URL): Promise<Response> {
  const url = typeof input === "string" ? input : (input as Request).url;
  if (url.includes("/tasks/current")) {
    return Promise.resolve(jsonResponse({ tasks: [], source: "mock" }));
  }
  if (url.includes("/workers/capacity")) {
    return Promise.resolve(jsonResponse({ max_workers: 4, source: "mock", workers: {} }));
  }
  if (url.includes("/tasks/")) {
    const taskIdMatch = url.match(/\/tasks\/([^?/]+)/);
    const tid = decodeURIComponent(taskIdMatch?.[1] ?? "unknown");
    return Promise.resolve(jsonResponse({ task_id: tid, status: "SUCCESS", result: null }));
  }
  return Promise.resolve(jsonResponse({}));
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.spyOn(globalThis, "fetch").mockImplementation(defaultFetchMock);
  window.localStorage.clear();
});

afterEach(async () => {
  // Allow pending microtasks (e.g., fetch callbacks) to settle before
  // unmounting, so stale setState calls don't leak into the next test.
  await act(() => new Promise((r) => setTimeout(r, 0)));
  cleanup();
  vi.restoreAllMocks();
});

describe("useTaskManager", () => {
  it("starts with idle status and empty task history", () => {
    const { result } = renderHook(() => useTaskManager());
    expect(result.current.status).toBe("idle");
    expect(result.current.taskId).toBeNull();
    expect(result.current.mainView).toBe("submission");
  });

  it("updateField updates form state", () => {
    const { result } = renderHook(() => useTaskManager());
    act(() => result.current.updateField("repo_path", "owner/repo"));
    expect(result.current.form.repo_path).toBe("owner/repo");
  });

  it("submitRun rejects when repo_path or prompt is empty", async () => {
    const { result } = renderHook(() => useTaskManager());

    // Clear the default form values so validation rejects
    act(() => {
      result.current.updateField("repo_path", "");
      result.current.updateField("prompt", "");
    });

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.submitRun(fakeEvent));

    expect(result.current.status).toBe("error");
    expect(result.current.updates).toEqual([
      "Error: Repository path and prompt are required.",
    ]);
  });

  it("submitRun posts to /build and adds task to history", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    fetchSpy.mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/build")) {
        return jsonResponse({ task_id: "task-1", status: "queued", backend: "claudecodecli" });
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());

    act(() => {
      result.current.updateField("repo_path", "owner/repo");
      result.current.updateField("prompt", "Fix the bug");
    });

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.submitRun(fakeEvent));

    expect(result.current.taskId).toBe("task-1");
    expect(result.current.mainView).toBe("monitor");
    expect(result.current.taskHistory).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ taskId: "task-1" }),
      ])
    );
    const buildCalls = fetchSpy.mock.calls.filter(([input]) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      return url.includes("/build");
    });
    expect(buildCalls.length).toBe(1);
  });

  it("submitRun handles network error gracefully", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/build")) {
        return errorResponse("Internal Server Error", 500);
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());
    act(() => {
      result.current.updateField("repo_path", "owner/repo");
      result.current.updateField("prompt", "Fix the bug");
    });

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.submitRun(fakeEvent));

    expect(result.current.status).toBe("error");
    expect(result.current.isPolling).toBe(false);
  });

  it("selectTask switches to monitor view", () => {
    const { result } = renderHook(() => useTaskManager());
    act(() => result.current.selectTask("task-42"));
    expect(result.current.taskId).toBe("task-42");
    expect(result.current.mainView).toBe("monitor");
  });

  it("openSubmissionView resets task state and shows overlay", () => {
    const { result } = renderHook(() => useTaskManager());

    act(() => result.current.selectTask("task-42"));
    act(() => result.current.openSubmissionView());

    expect(result.current.showSubmissionOverlay).toBe(true);
    expect(result.current.taskId).toBeNull();
    expect(result.current.isPolling).toBe(false);
    expect(result.current.status).toBe("idle");
  });

  it("persists task history to localStorage", async () => {
    const { result } = renderHook(() => useTaskManager());
    act(() => result.current.selectTask("task-99"));

    // Allow async effects to settle
    await act(() => Promise.resolve());

    const stored = window.localStorage.getItem(TASK_HISTORY_STORAGE_KEY);
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ taskId: "task-99" }),
      ])
    );
  });

  it("loads task history from localStorage on mount", () => {
    const saved = [
      {
        taskId: "restored-1",
        status: "SUCCESS",
        backend: "claudecodecli",
        repoPath: "owner/repo",
        createdAt: Date.now(),
        lastUpdatedAt: Date.now(),
      },
    ];
    window.localStorage.setItem(TASK_HISTORY_STORAGE_KEY, JSON.stringify(saved));

    const { result } = renderHook(() => useTaskManager());
    expect(result.current.taskHistory).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ taskId: "restored-1" }),
      ])
    );
  });

  it("removeToast is a no-op when no toasts exist", () => {
    const { result } = renderHook(() => useTaskManager());
    expect(result.current.toasts).toEqual([]);
    act(() => result.current.removeToast(999));
    expect(result.current.toasts).toEqual([]);
  });

  it("setTaskHistory clears history", () => {
    const { result } = renderHook(() => useTaskManager());
    act(() => result.current.selectTask("task-1"));
    expect(result.current.taskHistory.length).toBeGreaterThan(0);

    act(() => result.current.setTaskHistory([]));
    expect(result.current.taskHistory).toEqual([]);
  });

  it("activeTasks includes non-terminal tasks added via selectTask", () => {
    const { result } = renderHook(() => useTaskManager());
    // selectTask adds a task with status "monitoring" (non-terminal)
    act(() => result.current.selectTask("active-1"));
    expect(result.current.activeTasks).toEqual(
      expect.arrayContaining([expect.objectContaining({ taskId: "active-1" })])
    );
  });

  it("activeOutputText defaults to 'No updates yet.'", () => {
    const { result } = renderHook(() => useTaskManager());
    expect(result.current.activeOutputText).toBe("No updates yet.");
  });

  it("setMainView switches views", () => {
    const { result } = renderHook(() => useTaskManager());
    act(() => result.current.setMainView("schedules"));
    expect(result.current.mainView).toBe("schedules");
  });

  it("output tab and prefix filters are settable", () => {
    const { result } = renderHook(() => useTaskManager());
    act(() => result.current.setOutputTab("raw"));
    expect(result.current.outputTab).toBe("raw");
    act(() => result.current.setPrefixFilters({ "[INFO]": "only" }));
    expect(result.current.prefixFilters).toEqual({ "[INFO]": "only" });
  });

  it("taskById maps tasks by id", () => {
    const saved = [
      { taskId: "t1", status: "SUCCESS", backend: "e2e", repoPath: "a/b", createdAt: 1, lastUpdatedAt: 1 },
    ];
    window.localStorage.setItem(TASK_HISTORY_STORAGE_KEY, JSON.stringify(saved));

    const { result } = renderHook(() => useTaskManager());
    expect(result.current.taskById.get("t1")).toEqual(
      expect.objectContaining({ taskId: "t1", backend: "e2e" })
    );
  });

  it("fetchedCapacity starts as null", () => {
    const { result } = renderHook(() => useTaskManager());
    // Before the capacity poll resolves, fetchedCapacity is null
    expect(result.current.fetchedCapacity).toBeNull();
  });
});
