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

  it("fetchedCapacity is set after polling resolves", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/workers/capacity")) {
        return jsonResponse({ max_workers: 8 });
      }
      return defaultFetchMock(input);
    });
    const { result } = renderHook(() => useTaskManager());
    await act(() => new Promise((r) => setTimeout(r, 50)));
    expect(result.current.fetchedCapacity).toBe(8);
  });

  it("submitRun includes optional body fields when form has them", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    fetchSpy.mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/build")) {
        return jsonResponse({ task_id: "t-opts", status: "queued", backend: "e2e" });
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());
    act(() => {
      result.current.updateField("repo_path", "owner/repo");
      result.current.updateField("prompt", "Do the thing");
      result.current.updateField("github_token", "  ghp_abc  ");
      result.current.updateField("reference_repos", "a/b, c/d");
      result.current.updateField("model", " gpt-4 ");
      result.current.updateField("pr_number", " 42 ");
      result.current.updateField("tools", "tool1, tool2");
      result.current.updateField("skills", "skill1, skill2");
    });

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.submitRun(fakeEvent));

    const buildCall = fetchSpy.mock.calls.find(([input]) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      return url.includes("/build");
    });
    expect(buildCall).toBeDefined();
    const bodyStr = (buildCall![1] as RequestInit).body as string;
    const body = JSON.parse(bodyStr);
    expect(body.github_token).toBe("ghp_abc");
    expect(body.reference_repos).toEqual(["a/b", "c/d"]);
    expect(body.model).toBe("gpt-4");
    expect(body.pr_number).toBe(42);
    expect(body.tools).toEqual(["tool1", "tool2"]);
    expect(body.skills).toEqual(["skill1", "skill2"]);
  });

  it("submitRun includes issue_number when set", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    fetchSpy.mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/build")) {
        return jsonResponse({ task_id: "t-issue", status: "queued", backend: "e2e" });
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());
    act(() => {
      result.current.updateField("repo_path", "owner/repo");
      result.current.updateField("prompt", "Fix bug");
      result.current.updateField("issue_number", " 99 ");
    });

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.submitRun(fakeEvent));

    const buildCall = fetchSpy.mock.calls.find(([input]) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      return url.includes("/build");
    });
    const body = JSON.parse((buildCall![1] as RequestInit).body as string);
    expect(body.issue_number).toBe(99);
  });

  it("submitRun skips issue_number when not a valid number", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    fetchSpy.mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/build")) {
        return jsonResponse({ task_id: "t-issue-nan", status: "queued", backend: "e2e" });
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());
    act(() => {
      result.current.updateField("repo_path", "owner/repo");
      result.current.updateField("prompt", "Do it");
      result.current.updateField("issue_number", "abc");
    });

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.submitRun(fakeEvent));

    const buildCall = fetchSpy.mock.calls.find(([input]) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      return url.includes("/build");
    });
    const body = JSON.parse((buildCall![1] as RequestInit).body as string);
    expect(body.issue_number).toBeUndefined();
  });

  it("submitRun skips pr_number when not a valid number", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    fetchSpy.mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/build")) {
        return jsonResponse({ task_id: "t-nan", status: "queued", backend: "e2e" });
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());
    act(() => {
      result.current.updateField("repo_path", "owner/repo");
      result.current.updateField("prompt", "Do it");
      result.current.updateField("pr_number", "not-a-number");
    });

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.submitRun(fakeEvent));

    const buildCall = fetchSpy.mock.calls.find(([input]) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      return url.includes("/build");
    });
    const body = JSON.parse((buildCall![1] as RequestInit).body as string);
    expect(body.pr_number).toBeUndefined();
  });

  it("submitRun includes create_issue when enabled", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    fetchSpy.mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/build")) {
        return jsonResponse({ task_id: "t-ci", status: "queued", backend: "e2e" });
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());
    act(() => {
      result.current.updateField("repo_path", "owner/repo");
      result.current.updateField("prompt", "Add feature");
      result.current.updateField("create_issue", true);
    });

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.submitRun(fakeEvent));

    const buildCall = fetchSpy.mock.calls.find(([input]) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      return url.includes("/build");
    });
    const body = JSON.parse((buildCall![1] as RequestInit).body as string);
    expect(body.create_issue).toBe(true);
  });

  it("submitRun omits create_issue when disabled", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    fetchSpy.mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/build")) {
        return jsonResponse({ task_id: "t-noci", status: "queued", backend: "e2e" });
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());
    act(() => {
      result.current.updateField("repo_path", "owner/repo");
      result.current.updateField("prompt", "Do something");
    });

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.submitRun(fakeEvent));

    const buildCall = fetchSpy.mock.calls.find(([input]) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      return url.includes("/build");
    });
    const body = JSON.parse((buildCall![1] as RequestInit).body as string);
    expect(body.create_issue).toBeUndefined();
  });

  it("primary polling updates status and stops on terminal status", async () => {
    vi.useFakeTimers();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    let pollCount = 0;

    fetchSpy.mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/tasks/") && !url.includes("/current")) {
        pollCount++;
        if (pollCount >= 2) {
          return jsonResponse({
            task_id: "t-poll",
            status: "SUCCESS",
            result: { updates: ["done"] },
          });
        }
        return jsonResponse({
          task_id: "t-poll",
          status: "running",
          result: { updates: ["working..."] },
        });
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());

    // Select a task to start polling
    act(() => result.current.selectTask("t-poll"));

    // Let the first poll resolve
    await act(async () => { await vi.advanceTimersByTimeAsync(100); });

    expect(result.current.isPolling).toBe(true);

    // Advance to next poll interval (3s)
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });

    // After terminal status, polling should stop
    expect(result.current.status).toBe("SUCCESS");
    expect(result.current.isPolling).toBe(false);

    vi.useRealTimers();
  });

  it("primary polling handles poll error gracefully", async () => {
    vi.useFakeTimers();
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/tasks/") && !url.includes("/current")) {
        return errorResponse("server error", 500);
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());
    act(() => result.current.selectTask("t-err"));

    await act(async () => { await vi.advanceTimersByTimeAsync(100); });

    expect(result.current.status).toBe("poll_error");
    expect(result.current.isPolling).toBe(false);

    vi.useRealTimers();
  });

  it("query-string initializes task_id and status", async () => {
    Object.defineProperty(window, "location", {
      value: { ...window.location, search: "?task_id=qs-task&status=running&repo_path=a/b" },
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useTaskManager());
    await act(() => new Promise((r) => setTimeout(r, 0)));

    expect(result.current.taskId).toBe("qs-task");
    expect(result.current.mainView).toBe("monitor");
    // Polling was started; it may have already completed if the mock resolved terminal
    expect(result.current.taskHistory).toEqual(
      expect.arrayContaining([expect.objectContaining({ taskId: "qs-task" })])
    );

    // Restore
    Object.defineProperty(window, "location", {
      value: { ...window.location, search: "" },
      writable: true,
      configurable: true,
    });
  });

  it("query-string error param sets error status", async () => {
    Object.defineProperty(window, "location", {
      value: { ...window.location, search: "?error=Something+failed" },
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useTaskManager());
    await act(() => new Promise((r) => setTimeout(r, 0)));

    expect(result.current.status).toBe("error");

    Object.defineProperty(window, "location", {
      value: { ...window.location, search: "" },
      writable: true,
      configurable: true,
    });
  });

  it("query-string sets form fields from URL params", async () => {
    Object.defineProperty(window, "location", {
      value: {
        ...window.location,
        search: "?repo_path=custom/repo&prompt=custom+prompt&backend=e2e&model=gpt-5&max_iterations=10",
      },
      writable: true,
      configurable: true,
    });

    const { result } = renderHook(() => useTaskManager());
    await act(() => new Promise((r) => setTimeout(r, 0)));

    expect(result.current.form.repo_path).toBe("custom/repo");
    expect(result.current.form.prompt).toBe("custom prompt");
    expect(result.current.form.backend).toBe("e2e");
    expect(result.current.form.model).toBe("gpt-5");
    expect(result.current.form.max_iterations).toBe(10);

    Object.defineProperty(window, "location", {
      value: { ...window.location, search: "" },
      writable: true,
      configurable: true,
    });
  });

  it("outputTab raw shows raw updates text", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/build")) {
        return jsonResponse({ task_id: "t-raw", status: "queued", backend: "e2e" });
      }
      if (url.includes("/tasks/") && !url.includes("/current")) {
        return jsonResponse({
          task_id: "t-raw",
          status: "SUCCESS",
          result: { updates: ["line1", "line2"] },
        });
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());

    // Submit to get some output
    act(() => {
      result.current.updateField("repo_path", "a/b");
      result.current.updateField("prompt", "test");
    });
    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.submitRun(fakeEvent));
    await act(() => new Promise((r) => setTimeout(r, 50)));

    // Switch to raw tab
    act(() => result.current.setOutputTab("raw"));
    expect(result.current.activeOutputText).toContain("line1");
  });

  it("outputTab payload shows JSON payload", () => {
    const { result } = renderHook(() => useTaskManager());
    act(() => result.current.setOutputTab("payload"));
    // When payload is null, should show "{}"
    expect(result.current.activeOutputText).toBe("{}");
  });

  it("current tasks discovery merges discovered tasks", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/tasks/current")) {
        return jsonResponse({
          tasks: [
            { task_id: "discovered-1", status: "running", backend: "e2e", repo_path: "o/r" },
          ],
        });
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());
    await act(() => new Promise((r) => setTimeout(r, 50)));

    // The task should be discovered and added to history
    expect(result.current.taskHistory).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ taskId: "discovered-1" }),
      ])
    );
  });

  it("runtimeDisplay returns null when no task is running", () => {
    const { result } = renderHook(() => useTaskManager());
    expect(result.current.runtimeDisplay).toBeNull();
  });

  it("taskInputs derives input items from payload", async () => {
    vi.useFakeTimers();
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/tasks/") && !url.includes("/current")) {
        return jsonResponse({
          task_id: "t-inputs",
          status: "SUCCESS",
          result: {
            repo_path: "owner/repo",
            prompt: "fix bug",
            backend: "e2e",
            model: "gpt-4",
            max_iterations: "5",
            no_pr: true,
            enable_execution: false,
            tools: ["tool1"],
            skills: ["sk1"],
          },
        });
      }
      return defaultFetchMock(input);
    });

    const { result } = renderHook(() => useTaskManager());
    act(() => result.current.selectTask("t-inputs"));
    await act(async () => { await vi.advanceTimersByTimeAsync(200); });

    const labels = result.current.taskInputs.map((i) => i.label);
    expect(labels).toContain("Repo");

    vi.useRealTimers();
  });
});
