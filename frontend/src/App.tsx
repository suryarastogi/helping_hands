import {
  type CSSProperties,
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

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

type WorkerCapacityResponse = {
  max_workers: number;
  source: string;
  workers: Record<string, number>;
};

type FormState = {
  repo_path: string;
  prompt: string;
  backend: Backend;
  model: string;
  max_iterations: number;
  pr_number: string;
  skills: string;
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

type ServerConfig = {
  in_docker: boolean;
  native_auth_default: boolean;
};

type ServiceHealth = {
  redis: "ok" | "error";
  db: "ok" | "error" | "na";
  workers: "ok" | "error";
};

type ServiceHealthState = {
  reachable: boolean;
  health: ServiceHealth | null;
};

type OutputTab = "updates" | "raw" | "payload";
type MainView = "submission" | "monitor";
type DashboardView = "classic" | "world";

type WorkerVariant = "bot-alpha" | "bot-round" | "bot-heavy" | "goose";

type CharacterStyle = {
  bodyColor: string;
  accentColor: string;
  skinColor: string;
  outlineColor: string;
  variant: WorkerVariant;
};

type SceneWorkerPhase = "arriving" | "active" | "leaving";

type SceneWorker = {
  taskId: string;
  slot: number;
  phase: SceneWorkerPhase;
  phaseChangedAt: number;
};

type PlayerPosition = {
  x: number;
  y: number;
};

type PlayerDirection = "down" | "up" | "left" | "right";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").trim();
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
  backend: "claudecodecli",
  model: "claude-opus-4-5",
  max_iterations: 6,
  pr_number: "",
  skills: "",
  no_pr: false,
  enable_execution: false,
  enable_web: false,
  use_native_cli_auth: false,
};

const DASHBOARD_VIEW_STORAGE_KEY = "helping_hands_dashboard_view_v1";
const SCENE_PHASE_DURATION_MS = 900;
const DEFAULT_WORLD_MAX_WORKERS = 8;

const PLAYER_MOVE_STEP = 1.2;
const PLAYER_SIZE = { width: 3.5, height: 4 };
const DESK_SIZE = { width: 8, height: 7 };
const OFFICE_BOUNDS = { minX: 4, maxX: 96, minY: 6, maxY: 92 };

const DEFAULT_CHARACTER_STYLE: CharacterStyle = {
  bodyColor: "#64748b",
  accentColor: "#94a3b8",
  skinColor: "#f2c7a7",
  outlineColor: "#020617",
  variant: "bot-alpha",
};

const PROVIDER_CHARACTER_DEFAULTS: Record<string, CharacterStyle> = {
  openai: {
    bodyColor: "#10a37f",
    accentColor: "#c7fff1",
    skinColor: "#d9f6ef",
    outlineColor: "#0b3e32",
    variant: "bot-alpha",
  },
  claude: {
    bodyColor: "#d97706",
    accentColor: "#ffe0b8",
    skinColor: "#f7ddbf",
    outlineColor: "#492709",
    variant: "bot-heavy",
  },
  gemini: {
    bodyColor: "#2563eb",
    accentColor: "#d5e4ff",
    skinColor: "#d7e3ff",
    outlineColor: "#14295c",
    variant: "bot-round",
  },
  goose: {
    bodyColor: "#ffffff",
    accentColor: "#f97316",
    skinColor: "#e2e8f0",
    outlineColor: "#334155",
    variant: "goose",
  },
  langgraph: {
    bodyColor: "#0891b2",
    accentColor: "#c6f7ff",
    skinColor: "#e0fbff",
    outlineColor: "#0d3f4d",
    variant: "bot-round",
  },
  atomic: {
    bodyColor: "#dc2626",
    accentColor: "#ffd1d1",
    skinColor: "#ffe4e4",
    outlineColor: "#4a1111",
    variant: "bot-heavy",
  },
  agent: {
    bodyColor: "#f59e0b",
    accentColor: "#ffe8bd",
    skinColor: "#fff0d1",
    outlineColor: "#55300a",
    variant: "bot-alpha",
  },
  e2e: {
    bodyColor: "#7c3aed",
    accentColor: "#e9d5ff",
    skinColor: "#f4e8ff",
    outlineColor: "#2f1b63",
    variant: "bot-round",
  },
  other: DEFAULT_CHARACTER_STYLE,
};

function providerFromBackend(backend: string): string {
  const normalized = backend.trim().toLowerCase();
  if (normalized.includes("claude")) {
    return "claude";
  }
  if (normalized.includes("gemini")) {
    return "gemini";
  }
  if (normalized.includes("codex") || normalized.includes("openai")) {
    return "openai";
  }
  if (normalized.includes("goose")) {
    return "goose";
  }
  if (normalized.includes("langgraph")) {
    return "langgraph";
  }
  if (normalized.includes("atomic")) {
    return "atomic";
  }
  if (normalized.includes("agent")) {
    return "agent";
  }
  if (normalized.includes("e2e")) {
    return "e2e";
  }
  return "other";
}

function formatProviderName(provider: string): string {
  if (provider === "openai") {
    return "OpenAI / Codex";
  }
  if (provider === "e2e") {
    return "E2E";
  }
  return provider.charAt(0).toUpperCase() + provider.slice(1);
}

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

function statusBlinkerColor(status: string): string {
  const tone = statusTone(status);
  if (tone === "ok") return "var(--success)";
  if (tone === "fail") return "var(--danger)";
  if (tone === "run") return "#eab308";
  return "#6b7280";
}

export function isTerminalTaskStatus(status: string): boolean {
  const normalized = status.trim().toUpperCase();
  return (
    normalized === "SUCCESS" ||
    normalized === "FAILURE" ||
    normalized === "REVOKED" ||
    normalized === "ERROR" ||
    normalized === "POLL_ERROR"
  );
}

type InputItem = {
  label: string;
  value: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  return value as Record<string, unknown>;
}

function readStringValue(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function readBoolishValue(value: unknown): string | null {
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value !== "string") {
    return null;
  }
  const normalized = value.trim().toLowerCase();
  if (normalized === "true" || normalized === "false") {
    return normalized;
  }
  return null;
}

function readSkillsValue(value: unknown): string | null {
  if (Array.isArray(value)) {
    const tokens = value
      .map((item) => String(item).trim())
      .filter((item) => item.length > 0);
    return tokens.length > 0 ? tokens.join(", ") : null;
  }
  return readStringValue(value);
}

async function fetchWorkerCapacity(): Promise<number | null> {
  try {
    const response = await fetch(apiUrl(`/workers/capacity?_=${Date.now()}`), {
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    const data = (await response.json()) as WorkerCapacityResponse;
    if (typeof data.max_workers === "number" && data.max_workers >= 1) {
      return data.max_workers;
    }
    return null;
  } catch {
    return null;
  }
}

async function fetchServiceHealth(): Promise<ServiceHealthState> {
  try {
    const response = await fetch(apiUrl("/health/services"), { cache: "no-store" });
    if (!response.ok) {
      return { reachable: false, health: null };
    }
    const health = (await response.json()) as ServiceHealth;
    return { reachable: true, health };
  } catch {
    return { reachable: false, health: null };
  }
}

async function fetchServerConfig(): Promise<ServerConfig | null> {
  try {
    const response = await fetch(apiUrl("/config"), { cache: "no-store" });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as ServerConfig;
  } catch {
    return null;
  }
}

type DeskSlot = {
  id: string;
  left: number;
  top: number;
};

function buildDeskSlots(capacity: number): DeskSlot[] {
  const columns = 4;
  const rows = Math.max(1, Math.ceil(capacity / columns));
  const slots: DeskSlot[] = [];
  const leftStart = 14;
  const leftStep = 22;
  const topStart = 24;
  const topEnd = 82;
  const rowStep = rows > 1 ? (topEnd - topStart) / (rows - 1) : 0;

  for (let index = 0; index < capacity; index += 1) {
    const row = Math.floor(index / columns);
    const col = index % columns;
    slots.push({
      id: `desk-${index}`,
      left: leftStart + col * leftStep,
      top: Number((topStart + row * rowStep).toFixed(2)),
    });
  }

  return slots;
}

function checkDeskCollision(
  playerX: number,
  playerY: number,
  deskSlots: DeskSlot[]
): boolean {
  const playerLeft = playerX - PLAYER_SIZE.width / 2;
  const playerRight = playerX + PLAYER_SIZE.width / 2;
  const playerTop = playerY - PLAYER_SIZE.height / 2;
  const playerBottom = playerY + PLAYER_SIZE.height / 2;

  for (const desk of deskSlots) {
    const deskLeft = desk.left - DESK_SIZE.width / 2;
    const deskRight = desk.left + DESK_SIZE.width / 2;
    // Only use the bottom portion of the desk for collision so sprites can
    // walk "behind" the desk from above without stopping mid-way.
    const collisionTop = desk.top + DESK_SIZE.height * 0.1;
    const deskBottom = desk.top + DESK_SIZE.height / 2;

    const overlapsX = playerRight > deskLeft && playerLeft < deskRight;
    const overlapsY = playerBottom > collisionTop && playerTop < deskBottom;

    if (overlapsX && overlapsY) {
      return true;
    }
  }

  return false;
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

    const next = [...items];
    next[idx] = updated;
    return next;
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
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState("idle");
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [updates, setUpdates] = useState<string[]>([]);
  const [outputTab, setOutputTab] = useState<OutputTab>("updates");
  const [mainView, setMainView] = useState<MainView>("submission");
  const [isPolling, setIsPolling] = useState(false);
  const [taskHistory, setTaskHistory] = useState<TaskHistoryItem[]>([]);
  const [dashboardView, setDashboardView] = useState<DashboardView>("classic");
  const [sceneWorkers, setSceneWorkers] = useState<SceneWorker[]>([]);
  const [maxOfficeWorkers, setMaxOfficeWorkers] = useState(DEFAULT_WORLD_MAX_WORKERS);
  const [playerPosition, setPlayerPosition] = useState<PlayerPosition>({ x: 50, y: 50 });
  const [playerDirection, setPlayerDirection] = useState<PlayerDirection>("down");
  const [isPlayerWalking, setIsPlayerWalking] = useState(false);
  const slotByTaskRef = useRef<Record<string, number>>({});
  const sceneRef = useRef<HTMLDivElement>(null);
  const [serviceHealthState, setServiceHealthState] = useState<ServiceHealthState | null>(null);


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

  const selectedTask = useMemo(
    () => (taskId ? taskHistory.find((item) => item.taskId === taskId) ?? null : null),
    [taskHistory, taskId]
  );

  const activeTasks = useMemo(
    () => taskHistory.filter((item) => !isTerminalTaskStatus(item.status)),
    [taskHistory]
  );

  const [fetchedCapacity, setFetchedCapacity] = useState<number | null>(null);

  const activeTaskIds = useMemo(() => new Set(activeTasks.map((task) => task.taskId)), [
    activeTasks,
  ]);

  const taskById = useMemo(() => {
    const map = new Map<string, TaskHistoryItem>();
    for (const task of taskHistory) {
      map.set(task.taskId, task);
    }
    return map;
  }, [taskHistory]);

  const deskSlots = useMemo(() => buildDeskSlots(maxOfficeWorkers), [maxOfficeWorkers]);

  const claimSlotForTask = useCallback(
    (activeTaskId: string, occupiedSlots: Set<number>): number => {
      const existing = slotByTaskRef.current[activeTaskId];
      if (
        typeof existing === "number" &&
        existing >= 0 &&
        existing < maxOfficeWorkers &&
        !occupiedSlots.has(existing)
      ) {
        occupiedSlots.add(existing);
        return existing;
      }

      for (let slot = 0; slot < maxOfficeWorkers; slot += 1) {
        if (!occupiedSlots.has(slot)) {
          occupiedSlots.add(slot);
          slotByTaskRef.current[activeTaskId] = slot;
          return slot;
        }
      }

      slotByTaskRef.current[activeTaskId] = 0;
      occupiedSlots.add(0);
      return 0;
    },
    [maxOfficeWorkers]
  );

  const sceneWorkerEntries = useMemo(() => {
    return sceneWorkers.flatMap((worker) => {
      const task = taskById.get(worker.taskId);
      const desk = deskSlots[worker.slot];
      if (!task || !desk) {
        return [];
      }

      const provider = providerFromBackend(task.backend);
      const style =
        PROVIDER_CHARACTER_DEFAULTS[provider] ?? PROVIDER_CHARACTER_DEFAULTS.other ?? DEFAULT_CHARACTER_STYLE;

      return [
        {
          ...worker,
          task,
          desk,
          isActive: activeTaskIds.has(worker.taskId),
          provider,
          style,
          spriteVariant: provider === "goose" ? ("goose" as WorkerVariant) : style.variant,
        },
      ];
    });
  }, [activeTaskIds, deskSlots, sceneWorkers, taskById]);

  const officeDeskRows = useMemo(() => Math.max(1, Math.ceil(maxOfficeWorkers / 2)), [
    maxOfficeWorkers,
  ]);

  const worldSceneStyle = useMemo<CSSProperties>(() => {
    const extraRows = Math.max(0, officeDeskRows - 4);
    return {
      minHeight: `${380 + extraRows * 92}px`,
    };
  }, [officeDeskRows]);

  const taskInputs = useMemo<InputItem[]>(() => {
    const root = asRecord(payload) ?? {};
    const result = asRecord(root.result);

    const readString = (keys: string[]): string | null => {
      for (const key of keys) {
        const fromResult = readStringValue(result?.[key]);
        if (fromResult) {
          return fromResult;
        }
        const fromRoot = readStringValue(root[key]);
        if (fromRoot) {
          return fromRoot;
        }
      }
      return null;
    };

    const readBoolish = (keys: string[]): string | null => {
      for (const key of keys) {
        const fromResult = readBoolishValue(result?.[key]);
        if (fromResult) {
          return fromResult;
        }
        const fromRoot = readBoolishValue(root[key]);
        if (fromRoot) {
          return fromRoot;
        }
      }
      return null;
    };

    const readSkills = (keys: string[]): string | null => {
      for (const key of keys) {
        const fromResult = readSkillsValue(result?.[key]);
        if (fromResult) {
          return fromResult;
        }
        const fromRoot = readSkillsValue(root[key]);
        if (fromRoot) {
          return fromRoot;
        }
      }
      return null;
    };

    const items: InputItem[] = [];

    const repoPath = readString(["repo_path", "repo"]) ?? selectedTask?.repoPath ?? null;
    const backend = readString(["backend", "runtime_backend"]) ?? selectedTask?.backend ?? null;
    const prompt = readString(["prompt"]);
    const model = readString(["model"]);
    const maxIterations = readString(["max_iterations"]);
    const prNumber = readString(["pr_number"]);
    const noPr = readBoolish(["no_pr"]);
    const enableExecution = readBoolish(["enable_execution"]);
    const enableWeb = readBoolish(["enable_web"]);
    const useNativeAuth = readBoolish(["use_native_cli_auth"]);
    const skills = readSkills(["skills"]);

    if (repoPath) {
      items.push({ label: "Repo", value: repoPath });
    }
    if (backend) {
      items.push({ label: "Backend", value: backend });
    }
    if (model) {
      items.push({ label: "Model", value: model });
    }
    if (maxIterations) {
      items.push({ label: "Max iterations", value: maxIterations });
    }
    if (prNumber) {
      items.push({ label: "PR number", value: prNumber });
    }
    if (noPr) {
      items.push({ label: "No PR", value: noPr });
    }
    if (enableExecution) {
      items.push({ label: "Execution tools", value: enableExecution });
    }
    if (enableWeb) {
      items.push({ label: "Web tools", value: enableWeb });
    }
    if (useNativeAuth) {
      items.push({ label: "Native CLI auth", value: useNativeAuth });
    }
    if (skills) {
      items.push({ label: "Skills", value: skills });
    }
    if (prompt) {
      items.push({ label: "Prompt", value: prompt });
    }

    return items;
  }, [payload, selectedTask]);

  useEffect(() => {
    setTaskHistory(loadTaskHistory());
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const savedView = window.localStorage.getItem(DASHBOARD_VIEW_STORAGE_KEY);
    if (savedView === "classic" || savedView === "world") {
      setDashboardView(savedView);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      window.localStorage.setItem(DASHBOARD_VIEW_STORAGE_KEY, dashboardView);
    } catch {
      // Ignore storage failures.
    }
  }, [dashboardView]);

  useEffect(() => {
    let cancelled = false;

    const refresh = async () => {
      const capacity = await fetchWorkerCapacity();
      if (!cancelled && capacity !== null) {
        setFetchedCapacity(capacity);
      }
    };

    void refresh();
    const handle = window.setInterval(() => {
      void refresh();
    }, 30_000);

    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  useEffect(() => {
    setMaxOfficeWorkers((current) =>
      Math.max(
        current,
        fetchedCapacity ?? DEFAULT_WORLD_MAX_WORKERS,
        activeTasks.length,
        DEFAULT_WORLD_MAX_WORKERS
      )
    );
  }, [activeTasks.length, fetchedCapacity]);

  useEffect(() => {
    const now = Date.now();
    setSceneWorkers((current) => {
      const activeIds = new Set(activeTasks.map((item) => item.taskId));
      const existingByTaskId = new Map(current.map((worker) => [worker.taskId, worker]));
      const occupiedSlots = new Set<number>();
      const next: SceneWorker[] = [];

      for (const task of activeTasks) {
        const existing = existingByTaskId.get(task.taskId);
        const slot = claimSlotForTask(task.taskId, occupiedSlots);
        if (!existing) {
          next.push({
            taskId: task.taskId,
            slot,
            phase: "arriving",
            phaseChangedAt: now,
          });
          continue;
        }
        if (existing.phase === "leaving") {
          next.push({
            ...existing,
            slot,
            phase: "arriving",
            phaseChangedAt: now,
          });
          continue;
        }
        if (existing.slot !== slot) {
          next.push({
            ...existing,
            slot,
          });
          continue;
        }
        next.push(existing);
      }

      for (const existing of current) {
        if (activeIds.has(existing.taskId)) {
          continue;
        }
        if (existing.phase === "leaving") {
          next.push(existing);
          continue;
        }
        next.push({
          ...existing,
          phase: "leaving",
          phaseChangedAt: now,
        });
      }

      return next.sort((a, b) => a.slot - b.slot);
    });
  }, [activeTasks, claimSlotForTask]);

  useEffect(() => {
    if (sceneWorkers.length === 0) {
      return;
    }

    const handle = window.setInterval(() => {
      const now = Date.now();
      setSceneWorkers((current) => {
        let hasChanges = false;
        const next: SceneWorker[] = [];

        for (const worker of current) {
          const elapsed = now - worker.phaseChangedAt;
          if (worker.phase === "arriving" && elapsed >= SCENE_PHASE_DURATION_MS) {
            next.push({
              ...worker,
              phase: "active",
              phaseChangedAt: now,
            });
            hasChanges = true;
            continue;
          }
          if (worker.phase === "leaving" && elapsed >= SCENE_PHASE_DURATION_MS) {
            delete slotByTaskRef.current[worker.taskId];
            hasChanges = true;
            continue;
          }
          next.push(worker);
        }

        return hasChanges ? next : current;
      });
    }, 180);

    return () => {
      window.clearInterval(handle);
    };
  }, [sceneWorkers.length]);

  useEffect(() => {
    if (dashboardView !== "world") {
      return;
    }

    const keysPressed = new Set<string>();
    let animationFrame: number | null = null;

    const movePlayer = () => {
      if (keysPressed.size === 0) {
        setIsPlayerWalking(false);
        animationFrame = null;
        return;
      }

      setIsPlayerWalking(true);

      setPlayerPosition((current) => {
        let newX = current.x;
        let newY = current.y;

        if (keysPressed.has("ArrowUp") || keysPressed.has("w")) {
          newY -= PLAYER_MOVE_STEP;
          setPlayerDirection("up");
        }
        if (keysPressed.has("ArrowDown") || keysPressed.has("s")) {
          newY += PLAYER_MOVE_STEP;
          setPlayerDirection("down");
        }
        if (keysPressed.has("ArrowLeft") || keysPressed.has("a")) {
          newX -= PLAYER_MOVE_STEP;
          setPlayerDirection("left");
        }
        if (keysPressed.has("ArrowRight") || keysPressed.has("d")) {
          newX += PLAYER_MOVE_STEP;
          setPlayerDirection("right");
        }

        newX = Math.max(OFFICE_BOUNDS.minX, Math.min(OFFICE_BOUNDS.maxX, newX));
        newY = Math.max(OFFICE_BOUNDS.minY, Math.min(OFFICE_BOUNDS.maxY, newY));

        if (checkDeskCollision(newX, newY, deskSlots)) {
          return current;
        }

        return { x: newX, y: newY };
      });

      animationFrame = requestAnimationFrame(movePlayer);
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      const key = event.key;
      const target = event.target as HTMLElement | null;
      const isTyping =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable;

      if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(key)) {
        event.preventDefault();
        if (!keysPressed.has(key)) {
          keysPressed.add(key);
          if (animationFrame === null) {
            animationFrame = requestAnimationFrame(movePlayer);
          }
        }
      } else if (["w", "a", "s", "d"].includes(key) && !isTyping) {
        event.preventDefault();
        if (!keysPressed.has(key)) {
          keysPressed.add(key);
          if (animationFrame === null) {
            animationFrame = requestAnimationFrame(movePlayer);
          }
        }
      }
    };

    const handleKeyUp = (event: KeyboardEvent) => {
      keysPressed.delete(event.key);
      if (keysPressed.size === 0) {
        setIsPlayerWalking(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      if (animationFrame !== null) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [dashboardView, deskSlots]);

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
    }, 10000);

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

      const skills = params.get("skills");
      if (skills) {
        next.skills = skills;
      }

      next.no_pr = parseBool(params.get("no_pr"));
      next.enable_execution = parseBool(params.get("enable_execution"));
      next.enable_web = parseBool(params.get("enable_web"));
      const nativeAuthParam = params.get("use_native_cli_auth");
      if (nativeAuthParam !== null) {
        next.use_native_cli_auth = parseBool(nativeAuthParam);
      }

      return next;
    });

    const error = params.get("error");
    if (error) {
      setStatus("error");
      setPayload({ error });
    }

    if (queryTaskId) {
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
    let cancelled = false;
    const check = async () => {
      const result = await fetchServiceHealth();
      if (!cancelled) {
        setServiceHealthState(result);
      }
    };
    void check();
    const handle = window.setInterval(() => void check(), 15_000);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const hasExplicitNativeAuth = params.get("use_native_cli_auth") !== null;
    if (hasExplicitNativeAuth) {
      return;
    }
    fetchServerConfig().then((config) => {
      if (config) {
        setForm((current) => ({
          ...current,
          use_native_cli_auth: config.native_auth_default,
        }));
      }
    });
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

        if (isTerminalTaskStatus(data.status)) {
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
        setIsPolling(false);
      }
    };

    void pollOnce();
    const handle = window.setInterval(() => {
      void pollOnce();
    }, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, [isPolling, taskId]);

  useEffect(() => {
    let cancelled = false;

    const pollTrackedTasks = async () => {
      const pendingTaskIds = taskHistory
        .filter((item) => !isTerminalTaskStatus(item.status))
        .map((item) => item.taskId)
        .filter((id) => !(isPolling && taskId === id));

      if (pendingTaskIds.length === 0) {
        return;
      }

      const patches = await Promise.all(
        pendingTaskIds.map(async (pendingTaskId): Promise<TaskHistoryPatch> => {
          try {
            const response = await fetch(
              apiUrl(`/tasks/${encodeURIComponent(pendingTaskId)}?_=${Date.now()}`),
              {
                cache: "no-store",
              }
            );
            if (!response.ok) {
              throw new Error(await parseError(response));
            }

            const data = (await response.json()) as TaskStatus &
              Record<string, unknown>;
            const root = asRecord(data);
            const result = asRecord(data.result);
            const backend =
              readStringValue(result?.backend) ?? readStringValue(root?.backend);
            const repoPath =
              readStringValue(result?.repo_path) ??
              readStringValue(result?.repo) ??
              readStringValue(root?.repo_path) ??
              readStringValue(root?.repo);

            return {
              taskId: data.task_id,
              status: data.status,
              backend: backend ?? undefined,
              repoPath: repoPath ?? undefined,
            };
          } catch {
            return {
              taskId: pendingTaskId,
              status: "poll_error",
            };
          }
        })
      );

      if (cancelled) {
        return;
      }

      setTaskHistory((current) => {
        let next = current;
        for (const patch of patches) {
          next = upsertTaskHistory(next, patch);
        }
        return next;
      });
    };

    void pollTrackedTasks();
    const handle = window.setInterval(() => {
      void pollTrackedTasks();
    }, 10000);

    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, [isPolling, taskHistory, taskId]);

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
  };

  const selectTask = (selectedTaskId: string) => {
    setMainView("monitor");
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
    setMainView("monitor");
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
    if (form.skills.trim()) {
      body.skills = form.skills
        .split(",")
        .map((item) => item.trim())
        .filter((item) => item.length > 0);
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
      setUpdates([`Error: ${String(error)}`]);
      setIsPolling(false);
    }
  };

  const blinkerColor = statusBlinkerColor(status);
  const isBlinkerAnimated = statusTone(status) === "run";

  const serviceHealthIndicators: { key: string; label: string; state: "ok" | "error" | "na" | null }[] = [
    {
      key: "api",
      label: "api",
      state: serviceHealthState === null ? null : serviceHealthState.reachable ? "ok" : "error",
    },
    {
      key: "redis",
      label: "redis",
      state: serviceHealthState?.health?.redis ?? null,
    },
    {
      key: "db",
      label: "db",
      state: serviceHealthState?.health?.db ?? null,
    },
    {
      key: "workers",
      label: "workers",
      state: serviceHealthState?.health?.workers ?? null,
    },
  ];

  const serviceHealthBar = (
    <div className="service-health-bar" aria-label="Service health">
      {serviceHealthIndicators
        .filter((item) => item.state !== "na")
        .map((item) => {
          const color =
            item.state === "ok"
              ? "var(--success)"
              : item.state === "error"
                ? "var(--danger)"
                : "#4b5563";
          const title =
            item.state === null
              ? `${item.label}: checking…`
              : `${item.label}: ${item.state}`;
          return (
            <span key={item.key} className="service-health-item" title={title}>
              <span
                className={`service-health-dot${item.state === null ? " service-health-dot--checking" : ""}`}
                style={{ backgroundColor: color }}
              />
              <span className="service-health-label">{item.label}</span>
            </span>
          );
        })}
    </div>
  );

  const submissionCard = (
    <section className="card form-card compact-form">
      <form onSubmit={submitRun} className="form-grid-compact">
        <div className="form-inline-row">
          <input
            className="repo-input"
            value={form.repo_path}
            onChange={(event) => updateField("repo_path", event.target.value)}
            required
            placeholder="owner/repo"
          />
          <input
            className="prompt-input"
            value={form.prompt}
            onChange={(event) => updateField("prompt", event.target.value)}
            required
            placeholder="Prompt"
          />
          <button type="submit" className="submit-inline">Run</button>
        </div>

        <details className="compact-advanced">
          <summary>Advanced</summary>
          <div className="compact-advanced-body">
            <div className="row two-col">
              <label>
                Backend
                <select
                  value={form.backend}
                  onChange={(event) => updateField("backend", event.target.value as Backend)}
                >
                  {BACKEND_OPTIONS.map((backend) => (
                    <option key={backend} value={backend}>
                      {backend}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Model
                <input
                  value={form.model}
                  onChange={(event) => updateField("model", event.target.value)}
                  placeholder="gpt-5.2"
                />
              </label>
            </div>
            <div className="row two-col">
              <label>
                Max iterations
                <input
                  type="number"
                  min={1}
                  value={form.max_iterations}
                  onChange={(event) =>
                    updateField("max_iterations", Math.max(1, Number(event.target.value || 1)))
                  }
                />
              </label>
              <label>
                PR number
                <input
                  type="number"
                  min={1}
                  value={form.pr_number}
                  onChange={(event) => updateField("pr_number", event.target.value)}
                />
              </label>
            </div>
            <label>
              Skills
              <input
                value={form.skills}
                onChange={(event) => updateField("skills", event.target.value)}
                placeholder="execution,web,prd,ralph"
              />
            </label>
            <div className="row check-grid">
              <label className="check-row compact-check">
                <input
                  type="checkbox"
                  checked={form.no_pr}
                  onChange={(event) => updateField("no_pr", event.target.checked)}
                />
                No PR
              </label>
              <label className="check-row compact-check">
                <input
                  type="checkbox"
                  checked={form.enable_execution}
                  onChange={(event) => updateField("enable_execution", event.target.checked)}
                />
                Execution
              </label>
              <label className="check-row compact-check">
                <input
                  type="checkbox"
                  checked={form.enable_web}
                  onChange={(event) => updateField("enable_web", event.target.checked)}
                />
                Web
              </label>
              <label className="check-row compact-check">
                <input
                  type="checkbox"
                  checked={form.use_native_cli_auth}
                  onChange={(event) => updateField("use_native_cli_auth", event.target.checked)}
                />
                Native auth
              </label>
            </div>
          </div>
        </details>
      </form>
    </section>
  );

  const monitorCard = (
    <section className="card status-card compact-monitor">
      <div className="monitor-bar">
        <div className="monitor-bar-left">
          <h2 className="monitor-title">Output</h2>
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
        <div className="monitor-bar-right">
          <span
            className={`status-blinker${isBlinkerAnimated ? " pulse" : ""}`}
            style={{ backgroundColor: blinkerColor }}
            title={`${status}${isPolling ? " (polling)" : ""}`}
          />
          <span className="info-badge" title={taskId || "No task selected"}>
            i
          </span>
        </div>
      </div>
      <pre className="monitor-output">{activeOutputText}</pre>

      <details className="compact-advanced monitor-inputs">
        <summary>Task inputs</summary>
        <div className="compact-advanced-body">
          {taskInputs.length === 0 ? (
            <p className="inputs-empty">Inputs not available yet.</p>
          ) : (
            <dl className="inputs-grid">
              {taskInputs.map((item) => (
                <div key={item.label} className="input-item">
                  <dt>{item.label}</dt>
                  <dd>{item.value}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </details>
    </section>
  );

  return (
    <>
    <main className="page">
      <aside className="card task-list-card">
        <div className="view-toggle" role="tablist" aria-label="Dashboard view">
          <button
            type="button"
            role="tab"
            className={`view-toggle-btn${dashboardView === "classic" ? " active" : ""}`}
            aria-selected={dashboardView === "classic"}
            onClick={() => setDashboardView("classic")}
          >
            Classic view
          </button>
          <button
            type="button"
            role="tab"
            className={`view-toggle-btn${dashboardView === "world" ? " active" : ""}`}
            aria-selected={dashboardView === "world"}
            onClick={() => setDashboardView("world")}
          >
            Hand world
          </button>
        </div>
        <button
          type="button"
          className={`new-submission-button${
            dashboardView === "classic" && mainView === "submission" ? " active" : ""
          }`}
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
                  className={`task-row${taskId === item.taskId ? " active" : ""}`}
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
        {dashboardView === "classic" ? (
          mainView === "submission" ? (
            submissionCard
          ) : (
            monitorCard
          )
        ) : (
          <>
            <section className="card hand-world-card">
              <header className="header">
                <h1>agent office</h1>
                <p>{maxOfficeWorkers} desks &middot; click a worker to stream its output</p>
              </header>

              <div
                ref={sceneRef}
                className="world-scene office-scene"
                role="list"
                aria-label="Current office workers"
                style={worldSceneStyle}
                tabIndex={0}
              >
                <div className="office-border" aria-hidden="true" />
                <div className="office-main-floor" aria-hidden="true" />

                {deskSlots.map((slot) => (
                  <div
                    key={slot.id}
                    className="office-desk"
                    style={{ left: `${slot.left}%`, top: `${slot.top}%` }}
                    aria-hidden="true"
                  >
                    <span className="desk-screen" />
                    <span className="desk-keyboard" />
                    <span className="desk-chair" />
                  </div>
                ))}

                <div className="office-status-summary">
                  <div className="status-summary-header">Office Status</div>
                  <div className="status-summary-stat">
                    <span className="stat-icon">&#128187;</span>
                    <span>{maxOfficeWorkers} Desks</span>
                  </div>
                  <div className="status-summary-stat">
                    <span className="stat-icon">&#129302;</span>
                    <span>{sceneWorkerEntries.length} Active</span>
                  </div>
                  <div className="status-summary-stat">
                    <span className="stat-icon">&#128100;</span>
                    <span>You: ({Math.round(playerPosition.x)}, {Math.round(playerPosition.y)})</span>
                  </div>
                  <div className="status-summary-hint">Use arrow keys to walk</div>
                </div>

                <div
                  className={`human-player ${playerDirection}${isPlayerWalking ? " walking" : ""}`}
                  style={{
                    left: `${playerPosition.x}%`,
                    top: `${playerPosition.y}%`,
                  }}
                  aria-label="You (player character)"
                >
                  <span className="human-shadow" />
                  <span className="human-body">
                    <span className="human-helmet" />
                    <span className="human-visor" />
                    <span className="human-torso" />
                    <span className="human-arm human-arm-left" />
                    <span className="human-arm human-arm-right" />
                    <span className="human-leg human-leg-left" />
                    <span className="human-leg human-leg-right" />
                  </span>
                </div>

                {sceneWorkerEntries.map((worker) => (
                    <button
                      key={worker.taskId}
                      type="button"
                      role="listitem"
                      className={`worker-sprite ${worker.phase}${
                        taskId === worker.taskId ? " selected" : ""
                      }`}
                      style={{
                        left: `${worker.desk.left}%`,
                        top: `${worker.desk.top}%`,
                      }}
                      onClick={() => selectTask(worker.taskId)}
                      title={`${worker.task?.backend ?? "unknown"} • ${worker.taskId}`}
                      disabled={!worker.isActive}
                    >
                      <span className={`worker-art ${worker.spriteVariant}`} aria-hidden="true">
                        <span className="sprite-shadow" />
                        {worker.spriteVariant === "goose" ? (
                          <>
                            <span
                              className="goose-body"
                              style={{
                                backgroundColor: worker.style.bodyColor,
                                borderColor: worker.style.outlineColor,
                              }}
                            />
                            <span
                              className="goose-wing"
                              style={{
                                backgroundColor: worker.style.skinColor,
                              }}
                            />
                            <span
                              className="goose-head"
                              style={{
                                backgroundColor: worker.style.bodyColor,
                                borderColor: worker.style.outlineColor,
                              }}
                            />
                            <span
                              className="goose-beak"
                              style={{
                                backgroundColor: worker.style.accentColor,
                              }}
                            />
                            <span
                              className="goose-leg goose-leg-left"
                              style={{
                                backgroundColor: worker.style.accentColor,
                              }}
                            />
                            <span
                              className="goose-leg goose-leg-right"
                              style={{
                                backgroundColor: worker.style.accentColor,
                              }}
                            />
                            <span
                              className="goose-eye"
                              style={{
                                backgroundColor: worker.style.outlineColor,
                              }}
                            />
                          </>
                        ) : (
                          <>
                            <span
                              className="bot-head"
                              style={{
                                backgroundColor: worker.style.skinColor,
                                borderColor: worker.style.outlineColor,
                              }}
                            />
                            <span
                              className="bot-torso"
                              style={{
                                backgroundColor: worker.style.bodyColor,
                                borderColor: worker.style.outlineColor,
                              }}
                            />
                            <span
                              className="bot-core"
                              style={{
                                backgroundColor: worker.style.accentColor,
                              }}
                            />
                            <span
                              className="bot-eye bot-eye-left"
                              style={{
                                backgroundColor: worker.style.accentColor,
                              }}
                            />
                            <span
                              className="bot-eye bot-eye-right"
                              style={{
                                backgroundColor: worker.style.accentColor,
                              }}
                            />
                            <span
                              className="bot-leg bot-leg-left"
                              style={{
                                backgroundColor: worker.style.outlineColor,
                              }}
                            />
                            <span
                              className="bot-leg bot-leg-right"
                              style={{
                                backgroundColor: worker.style.outlineColor,
                              }}
                            />
                            <span
                              className="bot-antenna"
                              style={{
                                backgroundColor: worker.style.accentColor,
                              }}
                            />
                          </>
                        )}
                      </span>
                      <span className="worker-caption">
                        <strong>{shortTaskId(worker.taskId)}</strong>
                        <span>
                          {formatProviderName(worker.provider)} • {worker.task?.status ?? "unknown"}
                        </span>
                      </span>
                    </button>
                  ))}
              </div>

            </section>
            {submissionCard}
            {monitorCard}
          </>
        )}
      </div>
    </main>
    {serviceHealthBar}
    </>
  );
}
