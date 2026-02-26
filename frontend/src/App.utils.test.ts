import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  TASK_HISTORY_STORAGE_KEY,
  extractUpdates,
  loadTaskHistory,
  parseBool,
  parseError,
  parseOptimisticUpdates,
  shortTaskId,
  statusTone,
  upsertTaskHistory,
} from "./App";

describe("shortTaskId", () => {
  it("returns a short ID unchanged", () => {
    expect(shortTaskId("task-123")).toBe("task-123");
  });

  it("compacts long IDs for display", () => {
    const value = "1234567890abcdefghijklmnopq";
    expect(shortTaskId(value)).toBe("1234567890…jklmnopq");
  });
});

describe("statusTone", () => {
  it("maps successful statuses to ok", () => {
    expect(statusTone("SUCCESS")).toBe("ok");
  });

  it("maps failure statuses to fail", () => {
    expect(statusTone("failure")).toBe("fail");
    expect(statusTone("poll_error")).toBe("fail");
  });

  it("maps running statuses to run", () => {
    expect(statusTone("queued")).toBe("run");
    expect(statusTone("monitoring")).toBe("run");
  });

  it("maps unknown statuses to idle", () => {
    expect(statusTone("idle")).toBe("idle");
  });
});

describe("parsers", () => {
  it("parses boolean query values", () => {
    expect(parseBool("1")).toBe(true);
    expect(parseBool("true")).toBe(true);
    expect(parseBool("false")).toBe(false);
    expect(parseBool(null)).toBe(false);
  });

  it("extracts raw updates from result payloads", () => {
    expect(extractUpdates(null)).toEqual([]);
    expect(extractUpdates({})).toEqual([]);
    expect(extractUpdates({ updates: ["one", 2] })).toEqual(["one", "2"]);
  });

  it("summarizes optimistic update lines", () => {
    const parsed = parseOptimisticUpdates([
      "Initialization phase:",
      "Indexed files:",
      "- frontend/src/App.tsx",
      "- frontend/src/main.tsx",
      "Goals:",
      "1. first goal",
      "2. second goal",
      "Thinking",
      "/bin/zsh -lc \"npm run lint\" succeeded in 1.2s:",
      "[codexcli] still running (30s elapsed)",
      "I will poll /tasks/current next",
      "Execution context: scripted mode",
      ".zshenv:.:1: no such file or directory: /tmp/cargo/env",
    ]);

    expect(parsed).toEqual([
      "Initialization phase started.",
      "Repository index loaded (2 files).",
      "Loaded 2 initialization goals.",
      "Planning next step.",
      "Executed: npm run lint (1.2s)",
      "still running (30s elapsed)",
      "poll /tasks/current next",
      "Execution context confirmed (scripted, non-interactive).",
    ]);
  });
});

describe("parseError", () => {
  it("returns the JSON detail field when present", async () => {
    const response = new Response(JSON.stringify({ detail: "Invalid payload" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });

    await expect(parseError(response)).resolves.toBe("Invalid payload");
  });

  it("returns raw text for non-JSON payloads", async () => {
    const response = new Response("backend exploded", { status: 500 });
    await expect(parseError(response)).resolves.toBe("backend exploded");
  });
});

describe("task history helpers", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(1_700_000_000_000);
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
    window.localStorage.clear();
  });

  it("loads and normalizes persisted task history", () => {
    window.localStorage.setItem(
      TASK_HISTORY_STORAGE_KEY,
      JSON.stringify([
        {
          taskId: "task-a",
          status: "SUCCESS",
          backend: "codexcli",
          repoPath: "owner/repo",
          createdAt: "not-a-number",
          lastUpdatedAt: 123,
        },
        null,
      ])
    );

    expect(loadTaskHistory()).toEqual([
      {
        taskId: "task-a",
        status: "SUCCESS",
        backend: "codexcli",
        repoPath: "owner/repo",
        createdAt: 1_700_000_000_000,
        lastUpdatedAt: 123,
      },
    ]);
  });

  it("inserts and updates history entries", () => {
    const inserted = upsertTaskHistory([], {
      taskId: "task-1",
      status: "QUEUED",
      backend: "codexcli",
      repoPath: "owner/repo",
    });

    expect(inserted).toEqual([
      {
        taskId: "task-1",
        status: "QUEUED",
        backend: "codexcli",
        repoPath: "owner/repo",
        createdAt: 1_700_000_000_000,
        lastUpdatedAt: 1_700_000_000_000,
      },
    ]);

    vi.setSystemTime(1_700_000_000_100);

    const updated = upsertTaskHistory(inserted, {
      taskId: "task-1",
      status: "SUCCESS",
    });

    expect(updated).toEqual([
      {
        taskId: "task-1",
        status: "SUCCESS",
        backend: "codexcli",
        repoPath: "owner/repo",
        createdAt: 1_700_000_000_000,
        lastUpdatedAt: 1_700_000_000_100,
      },
    ]);
  });

  it("keeps ordering stable when updating existing entries", () => {
    const base = upsertTaskHistory(
      upsertTaskHistory([], {
        taskId: "task-1",
        status: "QUEUED",
        backend: "codexcli",
        repoPath: "owner/repo",
      }),
      {
        taskId: "task-2",
        status: "QUEUED",
        backend: "goose",
        repoPath: "owner/other",
      }
    );
    expect(base.map((item) => item.taskId)).toEqual(["task-2", "task-1"]);

    vi.setSystemTime(1_700_000_000_500);
    const updated = upsertTaskHistory(base, {
      taskId: "task-1",
      status: "SUCCESS",
    });
    expect(updated.map((item) => item.taskId)).toEqual(["task-2", "task-1"]);
    expect(updated[1].status).toBe("SUCCESS");
  });
});
