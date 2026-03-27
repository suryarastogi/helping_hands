import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";

import { DEFAULT_WORLD_MAX_WORKERS } from "../App.utils";
import type { ScheduleItem, TaskHistoryItem } from "../types";
import { useSceneWorkers, type UseSceneWorkersOptions } from "./useSceneWorkers";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeTask(taskId: string, backend = "claudecodecli"): TaskHistoryItem {
  return {
    taskId,
    status: "running",
    backend,
    repoPath: "owner/repo",
    createdAt: Date.now(),
    lastUpdatedAt: Date.now(),
  };
}

function makeSchedule(scheduleId: string, lastRunTaskId: string | null): ScheduleItem {
  return {
    schedule_id: scheduleId,
    name: `sched-${scheduleId}`,
    cron_expression: "0 * * * *",
    repo_path: "owner/repo",
    prompt: "test",
    backend: "claudecodecli",
    model: null,
    max_iterations: 3,
    pr_number: null,
    no_pr: false,
    enable_execution: false,
    enable_web: false,
    use_native_cli_auth: false,
    fix_ci: false,
    ci_check_wait_minutes: 0,
    github_token: null,
    reference_repos: [],
    tools: [],
    skills: [],
    project_management: false,
    enabled: true,
    created_at: "2026-03-26T00:00:00Z",
    last_run_at: null,
    last_run_task_id: lastRunTaskId,
    run_count: 0,
    next_run_at: null,
  };
}

function makeOptions(overrides: Partial<UseSceneWorkersOptions> = {}): UseSceneWorkersOptions {
  return {
    activeTasks: [],
    activeTaskIds: new Set(),
    taskById: new Map(),
    fetchedCapacity: null,
    schedules: [],
    ...overrides,
  };
}

// Prevent the 100ms phase-timer interval from running during tests.
beforeEach(() => {
  vi.spyOn(window, "setInterval").mockReturnValue(9999 as unknown as ReturnType<typeof setInterval>);
  vi.spyOn(window, "clearInterval").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useSceneWorkers", () => {
  it("returns default desk slots and empty workers when no tasks active", () => {
    // Options must be stable across renders to avoid infinite re-render loops.
    const opts = makeOptions();
    const { result } = renderHook(() => useSceneWorkers(opts));

    expect(result.current.maxOfficeWorkers).toBe(DEFAULT_WORLD_MAX_WORKERS);
    expect(result.current.deskSlots).toHaveLength(DEFAULT_WORLD_MAX_WORKERS);
    expect(result.current.sceneWorkerEntries).toEqual([]);
    expect(result.current.worldSceneStyle).toEqual({ minHeight: "380px" });
  });

  it("does not start phase timer when no workers exist", () => {
    const opts = makeOptions();
    renderHook(() => useSceneWorkers(opts));

    expect(window.setInterval).not.toHaveBeenCalled();
  });

  it("creates a scene worker in at-factory phase when a task becomes active", () => {
    const task = makeTask("task-1");
    const opts = makeOptions({
      activeTasks: [task],
      activeTaskIds: new Set(["task-1"]),
      taskById: new Map([["task-1", task]]),
    });

    const { result } = renderHook(() => useSceneWorkers(opts));

    expect(result.current.sceneWorkerEntries).toHaveLength(1);
    expect(result.current.sceneWorkerEntries[0].taskId).toBe("task-1");
    expect(result.current.sceneWorkerEntries[0].phase).toBe("at-factory");
    expect(result.current.sceneWorkerEntries[0].isActive).toBe(true);
  });

  it("starts phase timer when workers exist", () => {
    const task = makeTask("task-1");
    const opts = makeOptions({
      activeTasks: [task],
      activeTaskIds: new Set(["task-1"]),
      taskById: new Map([["task-1", task]]),
    });

    renderHook(() => useSceneWorkers(opts));

    expect(window.setInterval).toHaveBeenCalledWith(expect.any(Function), 100);
  });

  it("assigns unique desk slots to multiple workers", () => {
    const task1 = makeTask("task-1");
    const task2 = makeTask("task-2");
    const opts = makeOptions({
      activeTasks: [task1, task2],
      activeTaskIds: new Set(["task-1", "task-2"]),
      taskById: new Map([["task-1", task1], ["task-2", task2]]),
    });

    const { result } = renderHook(() => useSceneWorkers(opts));

    expect(result.current.sceneWorkerEntries).toHaveLength(2);
    const slots = result.current.sceneWorkerEntries.map((e) => e.slot);
    expect(new Set(slots).size).toBe(2);
  });

  it("scales maxOfficeWorkers up based on fetchedCapacity", () => {
    const opts1 = makeOptions();
    const opts2 = makeOptions({ fetchedCapacity: 20 });

    const { result, rerender } = renderHook(
      (props: UseSceneWorkersOptions) => useSceneWorkers(props),
      { initialProps: opts1 },
    );

    expect(result.current.maxOfficeWorkers).toBe(DEFAULT_WORLD_MAX_WORKERS);

    rerender(opts2);

    expect(result.current.maxOfficeWorkers).toBe(20);
    expect(result.current.deskSlots).toHaveLength(20);
  });

  it("enriches worker entries with goose provider and sprite variant", () => {
    const task = makeTask("task-1", "goose");
    const opts = makeOptions({
      activeTasks: [task],
      activeTaskIds: new Set(["task-1"]),
      taskById: new Map([["task-1", task]]),
    });

    const { result } = renderHook(() => useSceneWorkers(opts));

    expect(result.current.sceneWorkerEntries[0].provider).toBe("goose");
    expect(result.current.sceneWorkerEntries[0].spriteVariant).toBe("goose");
  });

  it("uses non-goose sprite variant for claude backend", () => {
    const task = makeTask("task-1", "claudecodecli");
    const opts = makeOptions({
      activeTasks: [task],
      activeTaskIds: new Set(["task-1"]),
      taskById: new Map([["task-1", task]]),
    });

    const { result } = renderHook(() => useSceneWorkers(opts));

    expect(result.current.sceneWorkerEntries[0].provider).toBe("claude");
    expect(result.current.sceneWorkerEntries[0].spriteVariant).not.toBe("goose");
  });

  it("annotates worker with schedule when matched by last_run_task_id", () => {
    const task = makeTask("task-1");
    const schedule = makeSchedule("sched-1", "task-1");
    const opts = makeOptions({
      activeTasks: [task],
      activeTaskIds: new Set(["task-1"]),
      taskById: new Map([["task-1", task]]),
      schedules: [schedule],
    });

    const { result } = renderHook(() => useSceneWorkers(opts));

    expect(result.current.sceneWorkerEntries[0].schedule).not.toBeNull();
    expect(result.current.sceneWorkerEntries[0].schedule?.schedule_id).toBe("sched-1");
  });

  it("returns null schedule when no matching schedule exists", () => {
    const task = makeTask("task-1");
    const opts = makeOptions({
      activeTasks: [task],
      activeTaskIds: new Set(["task-1"]),
      taskById: new Map([["task-1", task]]),
      schedules: [makeSchedule("sched-1", "other-task")],
    });

    const { result } = renderHook(() => useSceneWorkers(opts));

    expect(result.current.sceneWorkerEntries[0].schedule).toBeNull();
  });

  it("computes worldSceneStyle with increased minHeight for large capacity", () => {
    const opts = makeOptions({ fetchedCapacity: 20 });
    const { result } = renderHook(() => useSceneWorkers(opts));

    // 20 workers → 10 rows → 6 extra → 380 + 6*92 = 932px
    expect(result.current.worldSceneStyle).toEqual({ minHeight: "932px" });
  });

  it("moves worker to walking-to-exit when task is removed", () => {
    const task = makeTask("task-1");
    const taskById = new Map([["task-1", task]]);

    const activeOpts = makeOptions({
      activeTasks: [task],
      activeTaskIds: new Set(["task-1"]),
      taskById,
    });
    const emptyOpts = makeOptions({ taskById });

    const { result, rerender } = renderHook(
      (props: UseSceneWorkersOptions) => useSceneWorkers(props),
      { initialProps: activeOpts },
    );

    expect(result.current.sceneWorkerEntries[0].phase).toBe("at-factory");

    rerender(emptyOpts);

    expect(result.current.sceneWorkerEntries[0].phase).toBe("walking-to-exit");
  });

  it("re-activates worker to at-factory when removed task reappears", () => {
    const task = makeTask("task-1");
    const taskById = new Map([["task-1", task]]);

    const activeOpts = makeOptions({
      activeTasks: [task],
      activeTaskIds: new Set(["task-1"]),
      taskById,
    });
    const emptyOpts = makeOptions({ taskById });

    const { result, rerender } = renderHook(
      (props: UseSceneWorkersOptions) => useSceneWorkers(props),
      { initialProps: activeOpts },
    );

    rerender(emptyOpts);
    expect(result.current.sceneWorkerEntries[0].phase).toBe("walking-to-exit");

    rerender(activeOpts);
    expect(result.current.sceneWorkerEntries[0].phase).toBe("at-factory");
  });

  it("scales maxOfficeWorkers based on active task count exceeding default", () => {
    const tasks = Array.from({ length: 12 }, (_, i) => makeTask(`task-${i}`));
    const opts = makeOptions({
      activeTasks: tasks,
      activeTaskIds: new Set(tasks.map((t) => t.taskId)),
      taskById: new Map(tasks.map((t) => [t.taskId, t])),
    });

    const { result } = renderHook(() => useSceneWorkers(opts));

    expect(result.current.maxOfficeWorkers).toBeGreaterThanOrEqual(12);
    expect(result.current.sceneWorkerEntries).toHaveLength(12);
  });

  it("includes desk position data in worker entries", () => {
    const task = makeTask("task-1");
    const opts = makeOptions({
      activeTasks: [task],
      activeTaskIds: new Set(["task-1"]),
      taskById: new Map([["task-1", task]]),
    });

    const { result } = renderHook(() => useSceneWorkers(opts));

    const entry = result.current.sceneWorkerEntries[0];
    expect(entry.desk).toBeDefined();
    expect(typeof entry.desk.left).toBe("number");
    expect(typeof entry.desk.top).toBe("number");
    expect(entry.desk.id).toBeDefined();
  });

  it("clears phase timer on unmount", () => {
    const task = makeTask("task-1");
    const opts = makeOptions({
      activeTasks: [task],
      activeTaskIds: new Set(["task-1"]),
      taskById: new Map([["task-1", task]]),
    });

    const { unmount } = renderHook(() => useSceneWorkers(opts));

    unmount();

    expect(window.clearInterval).toHaveBeenCalled();
  });
});
