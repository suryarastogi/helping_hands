import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  TASK_HISTORY_STORAGE_KEY,
  apiUrl,
  asRecord,
  backendDisplayName,
  buildDeskSlots,
  checkDeskCollision,
  cronFrequency,
  extractUpdates,
  formatProviderName,
  isTerminalTaskStatus,
  loadTaskHistory,
  parseBool,
  parseError,
  parseOptimisticUpdates,
  providerFromBackend,
  readBoolishValue,
  readSkillsValue,
  readStringValue,
  repoName,
  shortTaskId,
  statusTone,
  upsertTaskHistory,
} from "./App";

describe("apiUrl", () => {
  it("returns the path unchanged when API_BASE is empty", () => {
    // API_BASE is "" by default in test env (no VITE_API_BASE_URL)
    expect(apiUrl("/health")).toBe("/health");
    expect(apiUrl("/api/tasks")).toBe("/api/tasks");
  });
});

describe("isTerminalTaskStatus", () => {
  it("identifies terminal statuses", () => {
    expect(isTerminalTaskStatus("SUCCESS")).toBe(true);
    expect(isTerminalTaskStatus("failure")).toBe(true);
    expect(isTerminalTaskStatus("REVOKED")).toBe(true);
    expect(isTerminalTaskStatus("ERROR")).toBe(true);
    expect(isTerminalTaskStatus("poll_error")).toBe(true);
  });

  it("identifies non-terminal statuses", () => {
    expect(isTerminalTaskStatus("QUEUED")).toBe(false);
    expect(isTerminalTaskStatus("STARTED")).toBe(false);
    expect(isTerminalTaskStatus("PENDING")).toBe(false);
    expect(isTerminalTaskStatus("RUNNING")).toBe(false);
    expect(isTerminalTaskStatus("idle")).toBe(false);
  });

  it("handles whitespace-padded input", () => {
    expect(isTerminalTaskStatus("  SUCCESS  ")).toBe(true);
    expect(isTerminalTaskStatus("  QUEUED  ")).toBe(false);
  });
});

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
    expect(statusTone("REVOKED")).toBe("fail");
  });

  it("maps running statuses to run", () => {
    expect(statusTone("queued")).toBe("run");
    expect(statusTone("monitoring")).toBe("run");
    expect(statusTone("STARTED")).toBe("run");
    expect(statusTone("PROGRESS")).toBe("run");
    expect(statusTone("SUBMITTING")).toBe("run");
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

  it("returns stringified JSON when detail is missing", async () => {
    const response = new Response(JSON.stringify({ error: "oops" }), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    });
    await expect(parseError(response)).resolves.toBe('{"error":"oops"}');
  });

  it("returns HTTP status when body is empty", async () => {
    const response = new Response("", { status: 503 });
    await expect(parseError(response)).resolves.toBe("HTTP 503");
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

describe("backendDisplayName", () => {
  it("returns a friendly name for e2e", () => {
    expect(backendDisplayName("e2e")).toBe("Smoke Test (internal)");
  });

  it("passes through other backends unchanged", () => {
    expect(backendDisplayName("codexcli")).toBe("codexcli");
    expect(backendDisplayName("claudecodecli")).toBe("claudecodecli");
  });
});

describe("providerFromBackend", () => {
  it("maps claude backends", () => {
    expect(providerFromBackend("claudecodecli")).toBe("claude");
    expect(providerFromBackend("  ClaudeCodeCLI  ")).toBe("claude");
  });

  it("maps gemini backends", () => {
    expect(providerFromBackend("geminicli")).toBe("gemini");
  });

  it("maps codex/openai backends", () => {
    expect(providerFromBackend("codexcli")).toBe("openai");
    expect(providerFromBackend("openai-something")).toBe("openai");
  });

  it("maps opencode backends", () => {
    expect(providerFromBackend("opencodecli")).toBe("opencode");
  });

  it("maps goose backends", () => {
    expect(providerFromBackend("goose")).toBe("goose");
  });

  it("maps langgraph backends", () => {
    expect(providerFromBackend("basic-langgraph")).toBe("langgraph");
  });

  it("maps atomic backends", () => {
    expect(providerFromBackend("basic-atomic")).toBe("atomic");
  });

  it("maps agent backends", () => {
    expect(providerFromBackend("basic-agent")).toBe("agent");
  });

  it("maps e2e backends", () => {
    expect(providerFromBackend("e2e")).toBe("e2e");
  });

  it("returns other for unknown backends", () => {
    expect(providerFromBackend("unknown-backend")).toBe("other");
  });
});

describe("formatProviderName", () => {
  it("formats openai specially", () => {
    expect(formatProviderName("openai")).toBe("OpenAI / Codex");
  });

  it("formats opencode specially", () => {
    expect(formatProviderName("opencode")).toBe("OpenCode");
  });

  it("formats e2e specially", () => {
    expect(formatProviderName("e2e")).toBe("Smoke Test");
  });

  it("capitalizes first letter for other providers", () => {
    expect(formatProviderName("claude")).toBe("Claude");
    expect(formatProviderName("gemini")).toBe("Gemini");
    expect(formatProviderName("goose")).toBe("Goose");
  });
});

describe("repoName", () => {
  it("extracts the last path segment", () => {
    expect(repoName("owner/repo")).toBe("repo");
    expect(repoName("/home/user/projects/myapp")).toBe("myapp");
  });

  it("strips trailing slashes", () => {
    expect(repoName("owner/repo/")).toBe("repo");
    expect(repoName("owner/repo///")).toBe("repo");
  });

  it("returns the full string when no slash", () => {
    expect(repoName("myrepo")).toBe("myrepo");
  });
});

describe("cronFrequency", () => {
  it("recognizes common cron presets", () => {
    expect(cronFrequency("* * * * *")?.label).toBe("1m");
    expect(cronFrequency("*/5 * * * *")?.label).toBe("5m");
    expect(cronFrequency("*/15 * * * *")?.label).toBe("15m");
    expect(cronFrequency("*/30 * * * *")?.label).toBe("30m");
    expect(cronFrequency("0 * * * *")?.label).toBe("1h");
    expect(cronFrequency("0 0 * * *")?.label).toBe("daily");
    expect(cronFrequency("0 0 * * 0")?.label).toBe("weekly");
    expect(cronFrequency("0 0 1 * *")?.label).toBe("monthly");
    expect(cronFrequency("0 9 * * 1-5")?.label).toBe("wkday");
  });

  it("handles fallback patterns", () => {
    expect(cronFrequency("*/3 * * * *")?.label).toBe("*/3");
    expect(cronFrequency("0 12 * * *")?.label).toBe("daily");
  });

  it("returns generic cron for unrecognized expressions", () => {
    expect(cronFrequency("15 3 * * 2,4")?.label).toBe("cron");
  });
});

describe("buildDeskSlots", () => {
  it("generates the correct number of slots", () => {
    expect(buildDeskSlots(1)).toHaveLength(1);
    expect(buildDeskSlots(4)).toHaveLength(4);
    expect(buildDeskSlots(8)).toHaveLength(8);
  });

  it("assigns unique IDs to each slot", () => {
    const slots = buildDeskSlots(4);
    const ids = slots.map((s) => s.id);
    expect(new Set(ids).size).toBe(4);
  });

  it("places slots in a grid layout", () => {
    const slots = buildDeskSlots(8);
    // First row: indices 0-3 should have the same top
    expect(slots[0].top).toBe(slots[1].top);
    expect(slots[0].top).toBe(slots[2].top);
    expect(slots[0].top).toBe(slots[3].top);
    // Second row should have a different top
    expect(slots[4].top).not.toBe(slots[0].top);
  });
});

describe("checkDeskCollision", () => {
  it("returns false when player is far from desks", () => {
    const desks = buildDeskSlots(1);
    expect(checkDeskCollision(50, 50, desks)).toBe(false);
  });

  it("returns true when player overlaps a desk", () => {
    const desks = buildDeskSlots(1);
    // Place player right on top of the first desk
    expect(checkDeskCollision(desks[0].left, desks[0].top + 2, desks)).toBe(true);
  });

  it("returns false with empty desk array", () => {
    expect(checkDeskCollision(50, 50, [])).toBe(false);
  });
});

describe("asRecord", () => {
  it("returns the object for valid records", () => {
    const obj = { key: "value" };
    expect(asRecord(obj)).toBe(obj);
  });

  it("returns null for non-objects", () => {
    expect(asRecord(null)).toBeNull();
    expect(asRecord(undefined)).toBeNull();
    expect(asRecord("string")).toBeNull();
    expect(asRecord(42)).toBeNull();
    expect(asRecord(true)).toBeNull();
  });
});

describe("readStringValue", () => {
  it("returns trimmed strings", () => {
    expect(readStringValue("hello")).toBe("hello");
    expect(readStringValue("  spaced  ")).toBe("spaced");
  });

  it("returns null for empty or whitespace-only strings", () => {
    expect(readStringValue("")).toBeNull();
    expect(readStringValue("   ")).toBeNull();
  });

  it("converts finite numbers to strings", () => {
    expect(readStringValue(42)).toBe("42");
    expect(readStringValue(0)).toBe("0");
    expect(readStringValue(3.14)).toBe("3.14");
  });

  it("returns null for non-string, non-number types", () => {
    expect(readStringValue(null)).toBeNull();
    expect(readStringValue(undefined)).toBeNull();
    expect(readStringValue(true)).toBeNull();
    expect(readStringValue({})).toBeNull();
  });

  it("returns null for non-finite numbers", () => {
    expect(readStringValue(Infinity)).toBeNull();
    expect(readStringValue(NaN)).toBeNull();
  });
});

describe("readBoolishValue", () => {
  it("converts booleans to string representation", () => {
    expect(readBoolishValue(true)).toBe("true");
    expect(readBoolishValue(false)).toBe("false");
  });

  it("accepts string true/false values", () => {
    expect(readBoolishValue("true")).toBe("true");
    expect(readBoolishValue("false")).toBe("false");
    expect(readBoolishValue("  True  ")).toBe("true");
    expect(readBoolishValue("  FALSE  ")).toBe("false");
  });

  it("returns null for non-boolean strings", () => {
    expect(readBoolishValue("yes")).toBeNull();
    expect(readBoolishValue("1")).toBeNull();
    expect(readBoolishValue("")).toBeNull();
  });

  it("returns null for non-string types", () => {
    expect(readBoolishValue(42)).toBeNull();
    expect(readBoolishValue(null)).toBeNull();
    expect(readBoolishValue(undefined)).toBeNull();
  });
});

describe("readSkillsValue", () => {
  it("joins array items into comma-separated string", () => {
    expect(readSkillsValue(["prd", "web"])).toBe("prd, web");
  });

  it("filters out empty array items", () => {
    expect(readSkillsValue(["prd", "", "  ", "web"])).toBe("prd, web");
  });

  it("returns null for empty array", () => {
    expect(readSkillsValue([])).toBeNull();
  });

  it("falls back to readStringValue for non-arrays", () => {
    expect(readSkillsValue("prd, web")).toBe("prd, web");
    expect(readSkillsValue(42)).toBe("42");
    expect(readSkillsValue(null)).toBeNull();
  });
});

describe("parseOptimisticUpdates edge cases", () => {
  it("handles bold markdown lines", () => {
    const result = parseOptimisticUpdates(["**Important update**"]);
    expect(result).toEqual(["Important update"]);
  });

  it("handles exec keyword alone", () => {
    const result = parseOptimisticUpdates(["exec"]);
    expect(result).toEqual([]);
  });

  it("handles mcp startup lines", () => {
    const result = parseOptimisticUpdates(["mcp startup: loaded 3 tools"]);
    expect(result).toEqual(["MCP startup: loaded 3 tools"]);
  });

  it("handles Repository root lines", () => {
    const result = parseOptimisticUpdates(["Repository root: /tmp/repo"]);
    expect(result).toEqual(["Repository root: /tmp/repo"]);
  });

  it("handles claudecodecli still running lines", () => {
    const result = parseOptimisticUpdates(["[claudecodecli] still running (60s elapsed)"]);
    expect(result).toEqual(["still running (60s elapsed)"]);
  });

  it("handles failed execution lines", () => {
    const result = parseOptimisticUpdates(['/bin/zsh -lc "npm run build" failed in 5.3s:']);
    expect(result).toEqual(["Failed: npm run build (5.3s)"]);
  });

  it("skips lines longer than 250 chars", () => {
    const longLine = "a".repeat(251);
    const result = parseOptimisticUpdates([longLine]);
    expect(result).toEqual([]);
  });

  it("skips lines starting with dash-space", () => {
    const result = parseOptimisticUpdates(["- some list item"]);
    expect(result).toEqual([]);
  });

  it("deduplicates consecutive identical lines", () => {
    const result = parseOptimisticUpdates(["Thinking", "Thinking"]);
    expect(result).toEqual(["Planning next step."]);
  });

  it("flushes indexed files at end of input", () => {
    const result = parseOptimisticUpdates(["Indexed files:", "- a.ts", "- b.ts"]);
    expect(result).toEqual(["Repository index loaded (2 files)."]);
  });

  it("flushes goals at end of input", () => {
    const result = parseOptimisticUpdates(["Goals:", "1. first", "2. second"]);
    expect(result).toEqual(["Loaded 2 initialization goals."]);
  });

  it("handles transition from indexed files to non-file line", () => {
    const result = parseOptimisticUpdates([
      "Indexed files:",
      "- a.ts",
      "Some other line",
    ]);
    expect(result).toEqual(["Repository index loaded (1 files).", "Some other line"]);
  });
});

describe("statusTone additional statuses", () => {
  it("maps RECEIVED to run", () => {
    expect(statusTone("RECEIVED")).toBe("run");
  });

  it("maps RETRY to run", () => {
    expect(statusTone("RETRY")).toBe("run");
  });

  it("maps SCHEDULED to run", () => {
    expect(statusTone("SCHEDULED")).toBe("run");
  });

  it("maps RESERVED to run", () => {
    expect(statusTone("RESERVED")).toBe("run");
  });

  it("maps SENT to run", () => {
    expect(statusTone("SENT")).toBe("run");
  });

  it("maps ERROR to idle (not a recognized terminal tone)", () => {
    expect(statusTone("ERROR")).toBe("idle");
  });

  it("maps unknown statuses case-insensitively", () => {
    expect(statusTone("  queued  ")).toBe("run");
    expect(statusTone("Failure")).toBe("fail");
  });
});

describe("cronFrequency additional patterns", () => {
  it("matches hourly fallback pattern for non-preset hourly cron", () => {
    const result = cronFrequency("0 */2 * * *");
    expect(result).not.toBeNull();
    expect(result!.label).toBe("hourly");
  });

  it("returns null for empty string", () => {
    const result = cronFrequency("");
    expect(result).not.toBeNull();
    expect(result!.label).toBe("cron");
  });

  it("matches minute-interval fallback for non-preset intervals", () => {
    const result = cronFrequency("*/7 * * * *");
    expect(result).not.toBeNull();
    expect(result!.label).toBe("*/7");
  });
});

describe("loadTaskHistory edge cases", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(1_700_000_000_000);
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
    window.localStorage.clear();
  });

  it("returns empty array for invalid JSON", () => {
    window.localStorage.setItem(TASK_HISTORY_STORAGE_KEY, "not-json{{{");
    expect(loadTaskHistory()).toEqual([]);
  });

  it("returns empty array for non-array JSON", () => {
    window.localStorage.setItem(TASK_HISTORY_STORAGE_KEY, JSON.stringify({ foo: "bar" }));
    expect(loadTaskHistory()).toEqual([]);
  });

  it("skips entries with empty taskId", () => {
    window.localStorage.setItem(
      TASK_HISTORY_STORAGE_KEY,
      JSON.stringify([
        { taskId: "", status: "SUCCESS", backend: "codexcli", repoPath: "owner/repo" },
        { taskId: "valid-id", status: "SUCCESS", backend: "codexcli", repoPath: "owner/repo" },
      ])
    );
    const result = loadTaskHistory();
    expect(result).toHaveLength(1);
    expect(result[0].taskId).toBe("valid-id");
  });

  it("returns empty array when localStorage is empty", () => {
    expect(loadTaskHistory()).toEqual([]);
  });

  it("enforces the 60-item limit", () => {
    const items = Array.from({ length: 70 }, (_, i) => ({
      taskId: `task-${i}`,
      status: "SUCCESS",
      backend: "codexcli",
      repoPath: "owner/repo",
      createdAt: 1_700_000_000_000,
      lastUpdatedAt: 1_700_000_000_000,
    }));
    window.localStorage.setItem(TASK_HISTORY_STORAGE_KEY, JSON.stringify(items));
    expect(loadTaskHistory()).toHaveLength(60);
  });
});

describe("upsertTaskHistory edge cases", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(1_700_000_000_000);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns items unchanged when patch has empty taskId", () => {
    const existing = [
      {
        taskId: "task-1",
        status: "SUCCESS",
        backend: "codexcli",
        repoPath: "owner/repo",
        createdAt: 1_700_000_000_000,
        lastUpdatedAt: 1_700_000_000_000,
      },
    ];
    const result = upsertTaskHistory(existing, { taskId: "" });
    expect(result).toBe(existing);
  });

  it("returns items unchanged when patch has whitespace-only taskId", () => {
    const existing = [
      {
        taskId: "task-1",
        status: "SUCCESS",
        backend: "codexcli",
        repoPath: "owner/repo",
        createdAt: 1_700_000_000_000,
        lastUpdatedAt: 1_700_000_000_000,
      },
    ];
    const result = upsertTaskHistory(existing, { taskId: "   " });
    expect(result).toBe(existing);
  });

  it("uses default values when patch has no optional fields", () => {
    const result = upsertTaskHistory([], { taskId: "new-task" });
    expect(result).toHaveLength(1);
    expect(result[0].status).toBe("queued");
    expect(result[0].backend).toBe("unknown");
    expect(result[0].repoPath).toBe("");
  });
});
