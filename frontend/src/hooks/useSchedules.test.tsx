import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useSchedules } from "./useSchedules";

// ---------------------------------------------------------------------------
// Fetch mock helpers
// ---------------------------------------------------------------------------

function makeResponse(data: unknown, status: number): Response {
  const body = typeof data === "string" ? data : JSON.stringify(data);
  const resp = {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(typeof data === "string" ? JSON.parse(data) : data),
    text: () => Promise.resolve(body),
    clone: () => makeResponse(data, status),
  } as unknown as Response;
  return resp;
}

function jsonResponse(data: unknown, status = 200): Response {
  return makeResponse(data, status);
}

function errorResponse(detail: string, status = 400): Response {
  return makeResponse({ detail }, status);
}

const SAMPLE_SCHEDULE = {
  schedule_id: "sched-1",
  name: "Daily docs",
  cron_expression: "0 0 * * *",
  repo_path: "owner/repo",
  prompt: "Update docs",
  backend: "claudecodecli",
  model: null,
  max_iterations: 6,
  pr_number: null,
  no_pr: false,
  enable_execution: false,
  enable_web: false,
  use_native_cli_auth: false,
  fix_ci: false,
  ci_check_wait_minutes: 3,
  github_token: null,
  reference_repos: [],
  tools: [],
  skills: ["docs"],
  project_management: false,
  enabled: true,
  created_at: "2026-03-23T00:00:00Z",
  last_run_at: null,
  last_run_task_id: null,
  run_count: 0,
  next_run_at: "2026-03-24T00:00:00Z",
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("useSchedules", () => {
  it("starts with empty state", () => {
    const { result } = renderHook(() => useSchedules());
    expect(result.current.schedules).toEqual([]);
    expect(result.current.scheduleError).toBeNull();
    expect(result.current.editingScheduleId).toBeNull();
    expect(result.current.showScheduleForm).toBe(false);
  });

  it("loadSchedules fetches and sets schedules", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse({ schedules: [SAMPLE_SCHEDULE], total: 1 }),
    );

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.loadSchedules());

    expect(result.current.schedules).toHaveLength(1);
    expect(result.current.schedules[0].name).toBe("Daily docs");
    expect(result.current.scheduleError).toBeNull();
  });

  it("loadSchedules sets error on failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      errorResponse("Server error", 500),
    );

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.loadSchedules());

    expect(result.current.schedules).toEqual([]);
    expect(result.current.scheduleError).toContain("Server error");
  });

  it("openNewScheduleForm sets showScheduleForm true", () => {
    const { result } = renderHook(() => useSchedules());
    act(() => result.current.openNewScheduleForm());

    expect(result.current.showScheduleForm).toBe(true);
    expect(result.current.editingScheduleId).toBeNull();
    expect(result.current.scheduleError).toBeNull();
  });

  it("cancelScheduleForm resets form state", () => {
    const { result } = renderHook(() => useSchedules());

    act(() => result.current.openNewScheduleForm());
    expect(result.current.showScheduleForm).toBe(true);

    act(() => result.current.cancelScheduleForm());
    expect(result.current.showScheduleForm).toBe(false);
    expect(result.current.editingScheduleId).toBeNull();
  });

  it("updateScheduleField updates a single form field", () => {
    const { result } = renderHook(() => useSchedules());
    act(() => result.current.updateScheduleField("name", "My schedule"));
    expect(result.current.scheduleForm.name).toBe("My schedule");
  });

  it("saveSchedule validates required fields", async () => {
    const { result } = renderHook(() => useSchedules());
    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;

    await act(() => result.current.saveSchedule(fakeEvent));

    expect(result.current.scheduleError).toBe(
      "Name, cron expression, repository path, and prompt are required.",
    );
  });

  it("saveSchedule posts and reloads on success", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ schedule_id: "new-1" }))
      .mockResolvedValueOnce(jsonResponse({ schedules: [SAMPLE_SCHEDULE], total: 1 }));

    const { result } = renderHook(() => useSchedules());

    act(() => {
      result.current.updateScheduleField("name", "Test");
      result.current.updateScheduleField("cron_expression", "0 0 * * *");
      result.current.updateScheduleField("repo_path", "owner/repo");
      result.current.updateScheduleField("prompt", "Do stuff");
    });

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.saveSchedule(fakeEvent));

    expect(fetchSpy).toHaveBeenCalledTimes(2);
    const [url, opts] = fetchSpy.mock.calls[0];
    expect(url).toContain("/schedules");
    expect((opts as RequestInit).method).toBe("POST");
    expect(result.current.scheduleError).toBeNull();
  });

  it("openEditScheduleForm fetches and populates form", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse(SAMPLE_SCHEDULE),
    );

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.openEditScheduleForm("sched-1"));

    expect(result.current.editingScheduleId).toBe("sched-1");
    expect(result.current.scheduleForm.name).toBe("Daily docs");
    expect(result.current.scheduleForm.cron_expression).toBe("0 0 * * *");
    expect(result.current.scheduleForm.skills).toBe("docs");
  });

  it("deleteSchedule calls DELETE and reloads", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(null, 204))
      .mockResolvedValueOnce(jsonResponse({ schedules: [], total: 0 }));

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.deleteSchedule("sched-1"));

    const [, opts] = fetchSpy.mock.calls[0];
    expect((opts as RequestInit).method).toBe("DELETE");
  });

  it("deleteSchedule does nothing when confirm is cancelled", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.deleteSchedule("sched-1"));

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("toggleSchedule calls enable/disable endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ ok: true }))
      .mockResolvedValueOnce(jsonResponse({ schedules: [], total: 0 }));

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.toggleSchedule("sched-1", false));

    expect(fetchSpy.mock.calls[0][0]).toContain("/schedules/sched-1/disable");
  });

  it("triggerSchedule calls trigger endpoint", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(window, "alert").mockImplementation(() => {});
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ task_id: "task-99", message: "ok" }))
      .mockResolvedValueOnce(jsonResponse({ schedules: [], total: 0 }));

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.triggerSchedule("sched-1"));

    expect(fetchSpy.mock.calls[0][0]).toContain("/schedules/sched-1/trigger");
  });

  it("triggerSchedule does nothing when confirm is cancelled", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.triggerSchedule("sched-1"));

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("triggerSchedule sets error on API failure", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      errorResponse("trigger failed", 500),
    );

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.triggerSchedule("sched-1"));

    expect(result.current.scheduleError).toContain("trigger failed");
  });

  it("toggleSchedule sets error on API failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      errorResponse("toggle failed", 500),
    );

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.toggleSchedule("sched-1", true));

    expect(result.current.scheduleError).toContain("toggle failed");
  });

  it("toggleSchedule calls enable endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ ok: true }))
      .mockResolvedValueOnce(jsonResponse({ schedules: [], total: 0 }));

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.toggleSchedule("sched-1", true));

    expect(fetchSpy.mock.calls[0][0]).toContain("/schedules/sched-1/enable");
  });

  it("openEditScheduleForm sets error on fetch failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      errorResponse("not found", 404),
    );

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.openEditScheduleForm("bad-id"));

    expect(result.current.scheduleError).toContain("not found");
    expect(result.current.editingScheduleId).toBeNull();
  });

  it("deleteSchedule sets error on fetch failure", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      errorResponse("delete failed", 500),
    );

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.deleteSchedule("sched-1"));

    expect(result.current.scheduleError).toContain("delete failed");
  });

  it("saveSchedule uses PUT when editing an existing schedule", async () => {
    // First, load a schedule for editing
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(SAMPLE_SCHEDULE));

    const { result } = renderHook(() => useSchedules());
    await act(() => result.current.openEditScheduleForm("sched-1"));

    // Now save — should use PUT
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ schedule_id: "sched-1" }))
      .mockResolvedValueOnce(jsonResponse({ schedules: [SAMPLE_SCHEDULE], total: 1 }));

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.saveSchedule(fakeEvent));

    const [url, opts] = fetchSpy.mock.calls[0];
    expect(url).toContain("/schedules/sched-1");
    expect((opts as RequestInit).method).toBe("PUT");
  });

  it("saveSchedule sets error on API failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      errorResponse("save failed", 500),
    );

    const { result } = renderHook(() => useSchedules());
    act(() => {
      result.current.updateScheduleField("name", "Test");
      result.current.updateScheduleField("cron_expression", "0 0 * * *");
      result.current.updateScheduleField("repo_path", "owner/repo");
      result.current.updateScheduleField("prompt", "Do stuff");
    });

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.saveSchedule(fakeEvent));

    expect(result.current.scheduleError).toContain("save failed");
  });

  it("saveSchedule includes optional fields when populated", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ schedule_id: "new-2" }))
      .mockResolvedValueOnce(jsonResponse({ schedules: [], total: 0 }));

    const { result } = renderHook(() => useSchedules());
    act(() => {
      result.current.updateScheduleField("name", "Full");
      result.current.updateScheduleField("cron_expression", "0 0 * * *");
      result.current.updateScheduleField("repo_path", "owner/repo");
      result.current.updateScheduleField("prompt", "Do stuff");
      result.current.updateScheduleField("model", "gpt-5.2");
      result.current.updateScheduleField("pr_number", "42");
      result.current.updateScheduleField("github_token", "ghp_abc");
      result.current.updateScheduleField("reference_repos", "foo/bar, baz/qux");
      result.current.updateScheduleField("tools", "read, write");
      result.current.updateScheduleField("skills", "docs, test");
    });

    const fakeEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(() => result.current.saveSchedule(fakeEvent));

    const body = JSON.parse((fetchSpy.mock.calls[0][1] as RequestInit).body as string);
    expect(body.model).toBe("gpt-5.2");
    expect(body.pr_number).toBe(42);
    expect(body.github_token).toBe("ghp_abc");
    expect(body.reference_repos).toEqual(["foo/bar", "baz/qux"]);
    expect(body.tools).toEqual(["read", "write"]);
    expect(body.skills).toEqual(["docs", "test"]);
  });
});
