import { type FormEvent, useEffect, useMemo, useState } from "react";

type Backend =
  | "e2e"
  | "basic-langgraph"
  | "basic-atomic"
  | "basic-agent"
  | "codexcli"
  | "claudecodecli"
  | "goose"
  | "geminicli";

type BuildResponse = {
  task_id: string;
  status: string;
  backend: string;
};

type TaskStatus = {
  task_id: string;
  status: string;
  result: Record<string, unknown> | null;
};

type CurrentTask = {
  task_id: string;
  status: string;
  backend?: string | null;
  repo_path?: string | null;
};

type CurrentTasksResponse = {
  tasks: CurrentTask[];
  source: string;
};

type FormState = {
  repo_path: string;
  prompt: string;
  backend: Backend;
  model: string;
  max_iterations: number;
  pr_number: string;
  no_pr: boolean;
  enable_execution: boolean;
  enable_web: boolean;
  use_native_cli_auth: boolean;
};

type TaskHistoryItem = {
  taskId: string;
  status: string;
  backend: string;
  repoPath: string;
  createdAt: number;
  lastUpdatedAt: number;
};

type TaskHistoryPatch = {
  taskId: string;
  status?: string;
  backend?: string;
  repoPath?: string;
};

type OutputTab = "updates" | "raw" | "payload";
type MainView = "submission" | "monitor";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").trim();
const TERMINAL_STATUSES = new Set(["SUCCESS", "FAILURE", "REVOKED"]);
export const TASK_HISTORY_STORAGE_KEY = "helping_hands_task_history_v1";
const TASK_HISTORY_LIMIT = 60;
const BACKEND_OPTIONS: Backend[] = [
  "e2e",
  "basic-langgraph",
  "basic-atomic",
  "basic-agent",
  "codexcli",
  "claudecodecli",
  "goose",
  "geminicli",
];

const DEFAULT_PROMPT =
  "Update README.md with results of your smoke test. Keep changes minimal and safe.";

const INITIAL_FORM: FormState = {
  repo_path: "suryarastogi/helping_hands",
  prompt: DEFAULT_PROMPT,
  backend: "codexcli",
  model: "",
  max_iterations: 6,
  pr_number: "",
  no_pr: false,
  enable_execution: false,
  enable_web: false,
  use_native_cli_auth: false,
};

export function apiUrl(path: string): string {
  if (!API_BASE) {
    return path;
  }
  return `${API_BASE.replace(/\/$/, "")}${path}`;
}

export function shortTaskId(value: string): string {
  if (value.length <= 26) {
    return value;
  }
  return `${value.slice(0, 10)}…${value.slice(-8)}`;
}

export function statusTone(status: string): "ok" | "fail" | "run" | "idle" {
  const normalized = status.trim().toUpperCase();
  if (normalized === "SUCCESS") {
    return "ok";
  }
  if (normalized === "FAILURE" || normalized === "REVOKED" || normalized === "POLL_ERROR") {
    return "fail";
  }
  if (
    normalized === "QUEUED" ||
    normalized === "PENDING" ||
    normalized === "STARTED" ||
    normalized === "RUNNING" ||
    normalized === "RECEIVED" ||
    normalized === "RETRY" ||
    normalized === "PROGRESS" ||
    normalized === "SCHEDULED" ||
    normalized === "RESERVED" ||
    normalized === "SENT" ||
    normalized === "MONITORING" ||
    normalized === "SUBMITTING"
  ) {
    return "run";
  }
  return "idle";
}

export async function parseError(response: Response): Promise<string> {
  const responseClone = response.clone();
  try {
    const data = (await response.json()) as { detail?: string };
    if (typeof data?.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
    return JSON.stringify(data);
  } catch {
    const text = await responseClone.text().catch(() => "");
    return text || `HTTP ${response.status}`;
  }
}

export function parseBool(value: string | null): boolean {
  return value === "1" || value === "true";
}

export function extractUpdates(result: Record<string, unknown> | null): string[] {
  if (!result || typeof result !== "object") {
    return [];
  }
  const raw = result.updates;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.map((item) => String(item));
}

export function parseOptimisticUpdates(rawUpdates: string[]): string[] {
  const lines = rawUpdates.flatMap((entry) => String(entry).split(/\r?\n/));
  const parsed: string[] = [];
  let inIndexedFiles = false;
  let indexedFileCount = 0;
  let inGoals = false;
  let goalCount = 0;

  const pushUnique = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    if (parsed[parsed.length - 1] !== trimmed) {
      parsed.push(trimmed);
    }
  };

  const flushIndexedFiles = () => {
    if (!inIndexedFiles) {
      return;
    }
    pushUnique(`Repository index loaded (${indexedFileCount} files).`);
    inIndexedFiles = false;
    indexedFileCount = 0;
  };

  const flushGoals = () => {
    if (!inGoals) {
      return;
    }
    pushUnique(`Loaded ${goalCount} initialization goals.`);
    inGoals = false;
    goalCount = 0;
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    if (trimmed.includes(".zshenv:.:1: no such file or directory")) {
      continue;
    }

    if (trimmed === "Indexed files:") {
      flushGoals();
      inIndexedFiles = true;
      indexedFileCount = 0;
      continue;
    }
    if (trimmed === "Goals:") {
      flushIndexedFiles();
      inGoals = true;
      goalCount = 0;
      continue;
    }

    if (inIndexedFiles) {
      if (trimmed.startsWith("- ")) {
        indexedFileCount += 1;
        continue;
      }
      flushIndexedFiles();
    }

    if (inGoals) {
      if (/^\d+\./.test(trimmed)) {
        goalCount += 1;
        continue;
      }
      flushGoals();
    }

    if (trimmed.toLowerCase() === "thinking") {
      pushUnique("Planning next step.");
      continue;
    }

    if (trimmed.startsWith("Initialization phase:")) {
      pushUnique("Initialization phase started.");
      continue;
    }

    if (trimmed.startsWith("Execution context:")) {
      pushUnique("Execution context confirmed (scripted, non-interactive).");
      continue;
    }

    if (trimmed.startsWith("Repository root:")) {
      pushUnique(trimmed);
      continue;
    }

    if (trimmed.startsWith("mcp startup:")) {
      pushUnique(`MCP startup: ${trimmed.slice("mcp startup:".length).trim()}`);
      continue;
    }

    if (trimmed.startsWith("[codexcli] still running")) {
      pushUnique(trimmed.replace("[codexcli] ", ""));
      continue;
    }

    if (trimmed.startsWith("I will ")) {
      pushUnique(trimmed.slice("I will ".length));
      continue;
    }

    if (trimmed.startsWith("**") && trimmed.endsWith("**")) {
      pushUnique(trimmed.slice(2, -2));
      continue;
    }

    const execMatch = trimmed.match(
      /^\/bin\/\S+\s+-lc\s+"([^"]+)".*\s(succeeded|failed)\s+in\s+([^:]+):?$/
    );
    if (execMatch) {
      const [, command, outcome, duration] = execMatch;
      pushUnique(
        `${outcome === "succeeded" ? "Executed" : "Failed"}: ${command} (${duration.trim()})`
      );
      continue;
    }

    if (trimmed === "exec") {
      continue;
    }

    if (trimmed.length <= 180 && !trimmed.startsWith("- ")) {
      pushUnique(trimmed);
    }
  }

  flushIndexedFiles();
  flushGoals();
  return parsed;
}

export function loadTaskHistory(): TaskHistoryItem[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(TASK_HISTORY_STORAGE_KEY);
    if (!raw) {
      return [];
    }

    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    const now = Date.now();
    const items: TaskHistoryItem[] = [];

    for (const entry of parsed) {
      if (!entry || typeof entry !== "object") {
        continue;
      }

      const candidate = entry as Record<string, unknown>;
      const taskId = String(candidate.taskId ?? "").trim();
      if (!taskId) {
        continue;
      }

      const createdAtRaw = Number(candidate.createdAt);
      const lastUpdatedRaw = Number(candidate.lastUpdatedAt);

      items.push({
        taskId,
        status: String(candidate.status ?? "unknown"),
        backend: String(candidate.backend ?? "unknown"),
        repoPath: String(candidate.repoPath ?? ""),
        createdAt: Number.isFinite(createdAtRaw) ? createdAtRaw : now,
        lastUpdatedAt: Number.isFinite(lastUpdatedRaw) ? lastUpdatedRaw : now,
      });
    }

    return items.slice(0, TASK_HISTORY_LIMIT);
  } catch {
    return [];
  }
}

export function upsertTaskHistory(
  items: TaskHistoryItem[],
  patch: TaskHistoryPatch
): TaskHistoryItem[] {
  const taskId = patch.taskId.trim();
  if (!taskId) {
    return items;
  }

  const now = Date.now();
  const idx = items.findIndex((item) => item.taskId === taskId);

  if (idx >= 0) {
    const existing = items[idx];
    const updated: TaskHistoryItem = {
      ...existing,
      status: patch.status ?? existing.status,
      backend: patch.backend ?? existing.backend,
      repoPath: patch.repoPath ?? existing.repoPath,
      lastUpdatedAt: now,
    };

    return [updated, ...items.filter((_, index) => index !== idx)];
  }

  const next: TaskHistoryItem = {
    taskId,
    status: patch.status ?? "queued",
    backend: patch.backend ?? "unknown",
    repoPath: patch.repoPath ?? "",
    createdAt: now,
    lastUpdatedAt: now,
  };

  return [next, ...items].slice(0, TASK_HISTORY_LIMIT);
}

export default function App() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [taskIdInput, setTaskIdInput] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState("idle");
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [updates, setUpdates] = useState<string[]>([]);
  const [outputTab, setOutputTab] = useState<OutputTab>("updates");
  const [mainView, setMainView] = useState<MainView>("submission");
  const [isPolling, setIsPolling] = useState(false);
  const [taskHistory, setTaskHistory] = useState<TaskHistoryItem[]>([]);

  const payloadText = useMemo(() => {
    if (!payload) {
      return "{}";
    }
    return JSON.stringify(payload, null, 2);
  }, [payload]);

  const rawUpdatesText = useMemo(() => {
    if (updates.length === 0) {
      return "No raw output yet.";
    }
    return updates.join("\n");
  }, [updates]);

  const optimisticUpdatesText = useMemo(() => {
    const parsed = parseOptimisticUpdates(updates);
    if (parsed.length === 0) {
      return "No updates yet.";
    }
    return parsed.join("\n");
  }, [updates]);

  const activeOutputText = useMemo(() => {
    if (outputTab === "raw") {
      return rawUpdatesText;
    }
    if (outputTab === "payload") {
      return payloadText;
    }
    return optimisticUpdatesText;
  }, [optimisticUpdatesText, outputTab, payloadText, rawUpdatesText]);

  useEffect(() => {
    setTaskHistory(loadTaskHistory());
  }, []);

  useEffect(() => {
    let cancelled = false;

    const refreshCurrentTasks = async () => {
      try {
        const response = await fetch(apiUrl(`/tasks/current?_=${Date.now()}`), {
          cache: "no-store",
        });
        if (!response.ok) {
          return;
        }

        const data = (await response.json()) as CurrentTasksResponse;
        if (cancelled || !Array.isArray(data.tasks)) {
          return;
        }

        setTaskHistory((current) => {
          let next = current;
          for (const item of data.tasks) {
            const discoveredTaskId = String(item.task_id ?? "").trim();
            if (!discoveredTaskId) {
              continue;
            }

            next = upsertTaskHistory(next, {
              taskId: discoveredTaskId,
              status: String(item.status ?? "unknown"),
              backend:
                typeof item.backend === "string" && item.backend.trim()
                  ? item.backend.trim()
                  : undefined,
              repoPath:
                typeof item.repo_path === "string" && item.repo_path.trim()
                  ? item.repo_path.trim()
                  : undefined,
            });
          }
          return next;
        });
      } catch {
        // Dynamic task discovery is best-effort only.
      }
    };

    void refreshCurrentTasks();
    const handle = window.setInterval(() => {
      void refreshCurrentTasks();
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      window.localStorage.setItem(
        TASK_HISTORY_STORAGE_KEY,
        JSON.stringify(taskHistory)
      );
    } catch {
      // Ignore storage failures (e.g., private browsing restrictions).
    }
  }, [taskHistory]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    const queryTaskId = params.get("task_id");
    const queryStatus = params.get("status");

    setForm((current) => {
      const next: FormState = { ...current };

      const repoPath = params.get("repo_path");
      if (repoPath) {
        next.repo_path = repoPath;
      }

      const prompt = params.get("prompt");
      if (prompt) {
        next.prompt = prompt;
      }

      const backend = params.get("backend");
      if (backend && BACKEND_OPTIONS.includes(backend as Backend)) {
        next.backend = backend as Backend;
      }

      const model = params.get("model");
      if (model) {
        next.model = model;
      }

      const maxIterations = params.get("max_iterations");
      if (maxIterations) {
        const parsed = Number(maxIterations);
        if (!Number.isNaN(parsed) && parsed > 0) {
          next.max_iterations = parsed;
        }
      }

      const prNumber = params.get("pr_number");
      if (prNumber) {
        next.pr_number = prNumber;
      }

      next.no_pr = parseBool(params.get("no_pr"));
      next.enable_execution = parseBool(params.get("enable_execution"));
      next.enable_web = parseBool(params.get("enable_web"));
      next.use_native_cli_auth = parseBool(params.get("use_native_cli_auth"));

      return next;
    });

    const error = params.get("error");
    if (error) {
      setStatus("error");
      setPayload({ error });
    }

    if (queryTaskId) {
      setTaskIdInput(queryTaskId);
      setTaskId(queryTaskId);
      setMainView("monitor");
      setStatus(queryStatus || "queued");
      setIsPolling(true);
      setTaskHistory((current) =>
        upsertTaskHistory(current, {
          taskId: queryTaskId,
          status: queryStatus || "queued",
          backend: params.get("backend") ?? undefined,
          repoPath: params.get("repo_path") ?? undefined,
        })
      );
    }
  }, []);

  useEffect(() => {
    if (!taskId || !isPolling) {
      return;
    }

    let cancelled = false;

    const pollOnce = async () => {
      try {
        const response = await fetch(
          apiUrl(`/tasks/${encodeURIComponent(taskId)}?_=${Date.now()}`),
          {
            cache: "no-store",
          }
        );

        if (!response.ok) {
          const detail = await parseError(response);
          throw new Error(detail);
        }

        const data = (await response.json()) as TaskStatus;
        if (cancelled) {
          return;
        }

        setStatus(data.status);
        setPayload(data as unknown as Record<string, unknown>);
        setUpdates(extractUpdates(data.result));
        setTaskHistory((current) =>
          upsertTaskHistory(current, {
            taskId: data.task_id,
            status: data.status,
          })
        );

        if (TERMINAL_STATUSES.has(data.status)) {
          setIsPolling(false);
        }
      } catch (error) {
        if (cancelled) {
          return;
        }
        setStatus("poll_error");
        setPayload({ error: String(error) });
        setTaskHistory((current) =>
          upsertTaskHistory(current, {
            taskId,
            status: "poll_error",
          })
        );
      }
    };

    void pollOnce();
    const handle = window.setInterval(() => {
      void pollOnce();
    }, 2000);

    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, [isPolling, taskId]);

  const updateField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const openSubmissionView = () => {
    setMainView("submission");
    setIsPolling(false);
    setStatus("idle");
    setPayload(null);
    setUpdates([]);
    setTaskId(null);
    setTaskIdInput("");
  };

  const selectTask = (selectedTaskId: string) => {
    setMainView("monitor");
    setTaskIdInput(selectedTaskId);
    setTaskId(selectedTaskId);
    setStatus("monitoring");
    setPayload(null);
    setUpdates([]);
    setIsPolling(true);
    setTaskHistory((current) =>
      upsertTaskHistory(current, {
        taskId: selectedTaskId,
        status: "monitoring",
      })
    );
  };

  const submitRun = async (event: FormEvent) => {
    event.preventDefault();

    setStatus("submitting");
    setPayload(null);
    setUpdates([]);

    const repoPath = form.repo_path.trim();
    const body: Record<string, unknown> = {
      repo_path: repoPath,
      prompt: form.prompt.trim(),
      backend: form.backend,
      max_iterations: form.max_iterations,
      no_pr: form.no_pr,
      enable_execution: form.enable_execution,
      enable_web: form.enable_web,
      use_native_cli_auth: form.use_native_cli_auth,
    };

    if (form.model.trim()) {
      body.model = form.model.trim();
    }
    if (form.pr_number.trim()) {
      body.pr_number = Number(form.pr_number.trim());
    }

    try {
      const response = await fetch(apiUrl("/build"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const detail = await parseError(response);
        throw new Error(detail);
      }

      const data = (await response.json()) as BuildResponse;
      setMainView("monitor");
      setTaskId(data.task_id);
      setTaskIdInput(data.task_id);
      setStatus(data.status);
      setPayload(data as unknown as Record<string, unknown>);
      setIsPolling(true);
      setTaskHistory((current) =>
        upsertTaskHistory(current, {
          taskId: data.task_id,
          status: data.status,
          backend: data.backend,
          repoPath,
        })
      );
    } catch (error) {
      setStatus("error");
      setPayload({ error: String(error) });
      setIsPolling(false);
    }
  };

  const monitorTask = () => {
    const id = taskIdInput.trim();
    if (!id) {
      setStatus("error");
      setPayload({ error: "Provide a task ID first." });
      return;
    }
    setMainView("monitor");
    setTaskId(id);
    setStatus("monitoring");
    setPayload(null);
    setUpdates([]);
    setIsPolling(true);
    setTaskHistory((current) =>
      upsertTaskHistory(current, {
        taskId: id,
        status: "monitoring",
        repoPath: form.repo_path.trim(),
      })
    );
  };

  return (
    <main className="page">
      <aside className="card task-list-card">
        <button
          type="button"
          className={`new-submission-button${mainView === "submission" ? " active" : ""}`}
          onClick={openSubmissionView}
        >
          New submission
        </button>
        <div className="task-list-header">
          <h2>Submitted tasks</h2>
          <button
            type="button"
            className="text-button"
            disabled={taskHistory.length === 0}
            onClick={() => setTaskHistory([])}
          >
            Clear
          </button>
        </div>
        {taskHistory.length === 0 ? (
          <p className="empty-list">No tasks submitted yet.</p>
        ) : (
          <ul className="task-list">
            {taskHistory.map((item) => (
              <li key={item.taskId}>
                <button
                  type="button"
                  className={`task-row${
                    mainView === "monitor" && taskId === item.taskId ? " active" : ""
                  }`}
                  onClick={() => selectTask(item.taskId)}
                  title={item.taskId}
                >
                  <span className="task-row-top">
                    <code>{shortTaskId(item.taskId)}</code>
                    <span className={`status-pill ${statusTone(item.status)}`}>
                      {item.status}
                    </span>
                  </span>
                  <span className="task-row-meta">
                    {item.backend} • {item.repoPath || "manual"} •{" "}
                    {new Date(item.lastUpdatedAt).toLocaleTimeString()}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      <div className="main-column">
        {mainView === "submission" ? (
          <section className="card form-card">
            <header className="header">
              <h1>helping_hands runner</h1>
              <p>Submit runs to /build and track progress from /tasks/{`{task_id}`}</p>
            </header>

            <form onSubmit={submitRun} className="form-grid">
              <label>
                Repo path (owner/repo)
                <input
                  value={form.repo_path}
                  onChange={(event) => updateField("repo_path", event.target.value)}
                  required
                />
              </label>

              <label>
                Prompt
                <textarea
                  value={form.prompt}
                  onChange={(event) => updateField("prompt", event.target.value)}
                  required
                  rows={6}
                />
              </label>

              <div className="row two-col">
                <label>
                  Backend
                  <select
                    value={form.backend}
                    onChange={(event) =>
                      updateField("backend", event.target.value as Backend)
                    }
                  >
                    {BACKEND_OPTIONS.map((backend) => (
                      <option key={backend} value={backend}>
                        {backend}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Model (optional)
                  <input
                    value={form.model}
                    onChange={(event) => updateField("model", event.target.value)}
                    placeholder="gpt-5.2"
                  />
                </label>
              </div>

              <div className="row three-col">
                <label>
                  Max iterations
                  <input
                    type="number"
                    min={1}
                    value={form.max_iterations}
                    onChange={(event) =>
                      updateField(
                        "max_iterations",
                        Math.max(1, Number(event.target.value || 1))
                      )
                    }
                  />
                </label>

                <label>
                  PR number (optional)
                  <input
                    type="number"
                    min={1}
                    value={form.pr_number}
                    onChange={(event) => updateField("pr_number", event.target.value)}
                    placeholder="1"
                  />
                </label>

                <label>
                  Task ID (manual monitor)
                  <input
                    value={taskIdInput}
                    onChange={(event) => setTaskIdInput(event.target.value)}
                    placeholder="task-..."
                  />
                </label>
              </div>

              <div className="row three-col check-grid">
                <label className="check-row">
                  <input
                    type="checkbox"
                    checked={form.no_pr}
                    onChange={(event) => updateField("no_pr", event.target.checked)}
                  />
                  Disable final PR push/create
                </label>

                <label className="check-row">
                  <input
                    type="checkbox"
                    checked={form.enable_execution}
                    onChange={(event) =>
                      updateField("enable_execution", event.target.checked)
                    }
                  />
                  Enable execution tools
                </label>

                <label className="check-row">
                  <input
                    type="checkbox"
                    checked={form.enable_web}
                    onChange={(event) => updateField("enable_web", event.target.checked)}
                  />
                  Enable web tools
                </label>

                <label className="check-row">
                  <input
                    type="checkbox"
                    checked={form.use_native_cli_auth}
                    onChange={(event) =>
                      updateField("use_native_cli_auth", event.target.checked)
                    }
                  />
                  Use native CLI auth (Codex/Claude)
                </label>
              </div>

              <div className="actions">
                <button type="submit">Submit run</button>
                <button type="button" className="secondary" onClick={monitorTask}>
                  Monitor task
                </button>
              </div>
            </form>
          </section>
        ) : (
          <section className="card status-card">
            <div className="actions">
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setIsPolling(false);
                  setStatus("stopped");
                }}
              >
                Stop polling
              </button>
            </div>
            <div className="meta-grid">
              <div className="meta-item">
                <span className="meta-label">Status</span>
                <strong>{status}</strong>
              </div>
              <div className="meta-item">
                <span className="meta-label">Task</span>
                <strong>{taskId || "-"}</strong>
              </div>
              <div className="meta-item">
                <span className="meta-label">Polling</span>
                <strong>{isPolling ? "active" : "off"}</strong>
              </div>
            </div>

            <article className="output-pane">
              <div className="pane-header">
                <h2>Output</h2>
                <div className="pane-tabs" role="tablist" aria-label="Output mode">
                  <button
                    type="button"
                    role="tab"
                    className={`tab-btn${outputTab === "updates" ? " active" : ""}`}
                    aria-selected={outputTab === "updates"}
                    onClick={() => setOutputTab("updates")}
                  >
                    Updates
                  </button>
                  <button
                    type="button"
                    role="tab"
                    className={`tab-btn${outputTab === "raw" ? " active" : ""}`}
                    aria-selected={outputTab === "raw"}
                    onClick={() => setOutputTab("raw")}
                  >
                    Raw
                  </button>
                  <button
                    type="button"
                    role="tab"
                    className={`tab-btn${outputTab === "payload" ? " active" : ""}`}
                    aria-selected={outputTab === "payload"}
                    onClick={() => setOutputTab("payload")}
                  >
                    Payload
                  </button>
                </div>
              </div>
              <pre>{activeOutputText}</pre>
            </article>
          </section>
        )}
      </div>
    </main>
  );
}
