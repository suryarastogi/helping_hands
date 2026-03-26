import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import type { ScheduleItem, TaskHistoryItem } from "../types";
import { useSceneWorkers, type UseSceneWorkersOptions } from "./useSceneWorkers";

function makeTask(id: string, backend = "basic-langgraph"): TaskHistoryItem {
  return {
    taskId: id,
    status: "running",
    backend,
    repoPath: "/tmp/repo",
    createdAt: Date.now(),
    lastUpdatedAt: Date.now(),
  };
}

describe("useSceneWorkers", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns empty arrays when there are no active tasks", () => {
    const opts: UseSceneWorkersOptions = {
      activeTasks: [],
      maxOfficeWorkers: 3,
      deskSlots: [{ id: "desk-0", left: 100, top: 100 }],
      taskHistory: [],
      schedules: [],
    };
    const { result, unmount } = renderHook(() => useSceneWorkers(opts));
    expect(result.current.sceneWorkers).toEqual([]);
    unmount();
  });

  it("spawns a worker for active task", () => {
    const task = makeTask("task-1");
    const opts: UseSceneWorkersOptions = {
      activeTasks: [task],
      maxOfficeWorkers: 3,
      deskSlots: [{ id: "desk-0", left: 100, top: 100 }],
      taskHistory: [task],
      schedules: [],
    };
    const { result, unmount } = renderHook(() => useSceneWorkers(opts));
    expect(result.current.sceneWorkers).toHaveLength(1);
    expect(result.current.sceneWorkers[0].taskId).toBe("task-1");
    expect(result.current.sceneWorkers[0].phase).toBe("at-factory");
    unmount();
  });

  it("transitions to walking-to-exit on deactivation", () => {
    const task = makeTask("task-1");
    const active: UseSceneWorkersOptions = {
      activeTasks: [task],
      maxOfficeWorkers: 3,
      deskSlots: [{ id: "desk-0", left: 100, top: 100 }],
      taskHistory: [task],
      schedules: [],
    };
    const inactive: UseSceneWorkersOptions = { ...active, activeTasks: [] };
    const { result, rerender, unmount } = renderHook(
      (p: UseSceneWorkersOptions) => useSceneWorkers(p),
      { initialProps: active },
    );
    rerender(inactive);
    expect(result.current.sceneWorkers[0].phase).toBe("walking-to-exit");
    rerender(active);
    expect(result.current.sceneWorkers[0].phase).toBe("at-factory");
    unmount();
  });

  it("builds enriched entries with provider style and schedule matching", () => {
    const tasks = [makeTask("task-1"), makeTask("task-2", "cli-claude")];
    const schedule: ScheduleItem = {
      id: "sched-1",
      name: "Nightly",
      prompt: "test",
      repo_path: "/tmp/repo",
      backend: "basic-langgraph",
      cron_expression: "0 0 * * *",
      enabled: true,
      last_run_task_id: "task-1",
      created_at: "2026-03-26T00:00:00Z",
    };
    const opts: UseSceneWorkersOptions = {
      activeTasks: tasks,
      maxOfficeWorkers: 3,
      deskSlots: [{ id: "desk-0", left: 100, top: 100 }, { id: "desk-1", left: 200, top: 100 }],
      taskHistory: tasks,
      schedules: [schedule],
    };
    const { result, unmount } = renderHook(() => useSceneWorkers(opts));

    // Unique slot assignments.
    expect(result.current.sceneWorkers).toHaveLength(2);
    expect(new Set(result.current.sceneWorkers.map((w) => w.slot)).size).toBe(2);

    // Enriched entries.
    expect(result.current.sceneWorkerEntries).toHaveLength(2);
    const e1 = result.current.sceneWorkerEntries[0];
    expect(e1.style.bodyColor).toBeDefined();
    expect(e1.isActive).toBe(true);
    expect(e1.schedule).toBe(schedule);
    expect(result.current.sceneWorkerEntries[1].schedule).toBeNull();
    unmount();
  });

  it("spawns floating numbers for positive deltas only", () => {
    const opts: UseSceneWorkersOptions = {
      activeTasks: [],
      maxOfficeWorkers: 3,
      deskSlots: [{ id: "desk-0", left: 100, top: 100 }],
      taskHistory: [],
      schedules: [],
    };
    const { result, unmount } = renderHook(() => useSceneWorkers(opts));
    act(() => {
      result.current.spawnFloatingNumber("task-1", 0);
      result.current.spawnFloatingNumber("task-1", -1);
    });
    expect(result.current.floatingNumbers).toHaveLength(0);
    act(() => {
      result.current.spawnFloatingNumber("task-1", 5);
    });
    expect(result.current.floatingNumbers).toHaveLength(1);
    expect(result.current.floatingNumbers[0].value).toBe(5);
    expect(result.current.floatingNumbers[0].taskId).toBe("task-1");
    unmount();
  });
});
