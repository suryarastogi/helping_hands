/**
 * Pure utility functions and app-level constants extracted from App.tsx.
 *
 * This module contains no React imports — only types, constants, and
 * stateless helpers that the App component and its tests depend on.
 */

import {
  DESK_SIZE,
  FACTORY_COLLISION,
  INCINERATOR_COLLISION,
  PLAYER_SIZE,
} from "./constants";
import type {
  AccumulatedUsage,
  Backend,
  CharacterStyle,
  ClaudeUsageResponse,
  DeskSlot,
  FormState,
  PrefixFilterMode,
  ScheduleFormState,
  SceneWorkerPhase,
  ServerConfig,
  ServiceHealth,
  ServiceHealthState,
  TaskHistoryItem,
  TaskHistoryPatch,
  WorkerCapacityResponse,
} from "./types";

// ---------------------------------------------------------------------------
// API base
// ---------------------------------------------------------------------------

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").trim();

// ---------------------------------------------------------------------------
// App constants
// ---------------------------------------------------------------------------

export const TASK_HISTORY_STORAGE_KEY = "helping_hands_task_history_v1";
export const TASK_HISTORY_LIMIT = 60;

export const BACKEND_OPTIONS: Backend[] = [
  "e2e",
  "basic-langgraph",
  "basic-atomic",
  "basic-agent",
  "codexcli",
  "claudecodecli",
  "docker-sandbox-claude",
  "goose",
  "geminicli",
  "opencodecli",
  "devincli",
];

export function filterEnabledBackends(
  all: Backend[],
  enabled?: string[],
): Backend[] {
  if (!enabled || enabled.length === 0) return all;
  const set = new Set(enabled);
  return all.filter((b) => set.has(b));
}

export const DEFAULT_PROMPT =
  "Update README.md with results of your smoke test. Keep changes minimal and safe.";

export const INITIAL_FORM: FormState = {
  repo_path: "suryarastogi/helping_hands",
  prompt: DEFAULT_PROMPT,
  backend: "claudecodecli",
  model: "claude-opus-4-6",
  max_iterations: 6,
  pr_number: "",
  issue_number: "",
  create_issue: false,
  tools: "",
  skills: "",
  no_pr: false,
  enable_execution: false,
  enable_web: false,
  use_native_cli_auth: false,
  fix_ci: false,
  ci_check_wait_minutes: 3,
  github_token: "",
  reference_repos: "",
};

export const CRON_PRESETS: Record<string, string> = {
  every_minute: "* * * * *",
  every_5_minutes: "*/5 * * * *",
  every_15_minutes: "*/15 * * * *",
  every_30_minutes: "*/30 * * * *",
  hourly: "0 * * * *",
  daily: "0 0 * * *",
  weekly: "0 0 * * 0",
  monthly: "0 0 1 * *",
  weekdays: "0 9 * * 1-5",
};

export const INITIAL_SCHEDULE_FORM: ScheduleFormState = {
  name: "",
  cron_expression: "",
  repo_path: "suryarastogi/helping_hands",
  prompt: "",
  backend: "claudecodecli",
  model: "",
  max_iterations: 6,
  pr_number: "",
  no_pr: false,
  enable_execution: false,
  enable_web: false,
  use_native_cli_auth: false,
  fix_ci: false,
  ci_check_wait_minutes: 3,
  github_token: "",
  reference_repos: "",
  tools: "",
  skills: "",
  enabled: true,
};

export const PHASE_DURATION: Record<SceneWorkerPhase, number> = {
  "at-factory": 80,
  "walking-to-desk": 1500,
  "active": Infinity,
  "walking-to-exit": 1500,
  "at-exit": 400,
};

export const DEFAULT_WORLD_MAX_WORKERS = 8;

export const DEFAULT_CHARACTER_STYLE: CharacterStyle = {
  bodyColor: "#64748b",
  accentColor: "#94a3b8",
  skinColor: "#f2c7a7",
  outlineColor: "#020617",
  variant: "bot-alpha",
};

export const PROVIDER_CHARACTER_DEFAULTS: Record<string, CharacterStyle> = {
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
  opencode: {
    bodyColor: "#0d9488",
    accentColor: "#ccfbf1",
    skinColor: "#d5f5f0",
    outlineColor: "#134e4a",
    variant: "bot-alpha",
  },
  devin: {
    bodyColor: "#6366f1",
    accentColor: "#e0e7ff",
    skinColor: "#eef2ff",
    outlineColor: "#312e81",
    variant: "bot-heavy",
  },
  other: DEFAULT_CHARACTER_STYLE,
};

// ---------------------------------------------------------------------------
// Regex patterns
// ---------------------------------------------------------------------------

const PREFIX_RE = /^\[([^\]]+)\]/;
const API_COST_RE = /api:\s*\$([0-9]+(?:\.[0-9]+)?)/;

// ---------------------------------------------------------------------------
// Pure utility functions
// ---------------------------------------------------------------------------

export function defaultModelForBackend(backend: string): string {
  const normalized = backend.trim().toLowerCase();
  if (normalized.includes("codex") || normalized.includes("openai")) return "gpt-5.2";
  if (normalized.includes("claude")) return "claude-opus-4-6";
  if (normalized.includes("gemini")) return "gemini-2.5-pro";
  return "";
}

export function backendDisplayName(backend: string): string {
  if (backend === "e2e") return "Smoke Test (internal)";
  if (backend === "docker-sandbox-claude") return "Claude (Docker Sandbox)";
  return backend;
}

export function providerFromBackend(backend: string): string {
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
  if (normalized.includes("opencode")) {
    return "opencode";
  }
  if (normalized.includes("devin")) {
    return "devin";
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

export function formatProviderName(provider: string): string {
  if (provider === "openai") {
    return "OpenAI / Codex";
  }
  if (provider === "opencode") {
    return "OpenCode";
  }
  if (provider === "devin") {
    return "Devin";
  }
  if (provider === "e2e") {
    return "Smoke Test";
  }
  return provider.charAt(0).toUpperCase() + provider.slice(1);
}

export function apiUrl(path: string): string {
  if (!API_BASE) {
    return path;
  }
  return `${API_BASE.replace(/\/$/, "")}${path}`;
}

export function wsUrl(path: string): string {
  if (API_BASE) {
    const base = API_BASE.replace(/\/$/, "").replace(/^http/, "ws");
    return `${base}${path}`;
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}

export function shortTaskId(value: string): string {
  if (value.length <= 26) {
    return value;
  }
  return `${value.slice(0, 10)}…${value.slice(-8)}`;
}

export function repoName(repoPath: string): string {
  const trimmed = repoPath.replace(/\/+$/, "");
  const last = trimmed.split("/").pop();
  return last || trimmed;
}

export function cronFrequency(cron: string): { symbol: string; label: string } | null {
  const c = cron.trim();
  if (c === "* * * * *") return { symbol: "\u26A1", label: "1m" }; // ⚡
  if (c === "*/5 * * * *") return { symbol: "\uD83D\uDD04", label: "5m" }; // 🔄
  if (c === "*/15 * * * *") return { symbol: "\uD83D\uDD04", label: "15m" };
  if (c === "*/30 * * * *") return { symbol: "\uD83D\uDD04", label: "30m" };
  if (c === "0 * * * *") return { symbol: "\u23F0", label: "1h" }; // ⏰
  if (c === "0 0 * * *") return { symbol: "\u2600", label: "daily" }; // ☀
  if (c === "0 0 * * 0") return { symbol: "\uD83D\uDCC5", label: "weekly" }; // 📅
  if (c === "0 0 1 * *") return { symbol: "\uD83D\uDDD3", label: "monthly" }; // 🗓
  if (c === "0 9 * * 1-5") return { symbol: "\uD83D\uDCBC", label: "wkday" }; // 💼
  // Fallback: check common patterns
  if (/^\*\/\d+\s/.test(c)) return { symbol: "\uD83D\uDD04", label: c.split(" ")[0] };
  if (/^0\s\*/.test(c)) return { symbol: "\u23F0", label: "hourly" };
  if (/^0\s\d+\s\*\s\*\s\*$/.test(c)) return { symbol: "\u2600", label: "daily" };
  return { symbol: "\uD83D\uDD01", label: "cron" }; // 🔁 generic fallback
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

export function statusBlinkerColor(status: string): string {
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

export function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  return value as Record<string, unknown>;
}

export function readStringValue(value: unknown): string | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function readBoolishValue(value: unknown): string | null {
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

export function readSkillsValue(value: unknown): string | null {
  if (Array.isArray(value)) {
    const tokens = value
      .map((item) => String(item).trim())
      .filter((item) => item.length > 0);
    return tokens.length > 0 ? tokens.join(", ") : null;
  }
  return readStringValue(value);
}

// ---------------------------------------------------------------------------
// Async fetch helpers
// ---------------------------------------------------------------------------

export async function fetchWorkerCapacity(): Promise<number | null> {
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

export async function fetchServiceHealth(): Promise<ServiceHealthState> {
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

export async function fetchClaudeUsage(force = false): Promise<ClaudeUsageResponse> {
  try {
    const qs = force ? `force=true&_=${Date.now()}` : `_=${Date.now()}`;
    const response = await fetch(apiUrl(`/health/claude-usage?${qs}`), {
      cache: "no-store",
    });
    if (!response.ok) {
      return { levels: [], error: `Server returned ${response.status}`, fetched_at: new Date().toISOString() };
    }
    return (await response.json()) as ClaudeUsageResponse;
  } catch (err) {
    return { levels: [], error: `Fetch failed: ${err instanceof Error ? err.message : String(err)}`, fetched_at: new Date().toISOString() };
  }
}

export async function fetchServerConfig(): Promise<ServerConfig | null> {
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

// ---------------------------------------------------------------------------
// Scene geometry helpers
// ---------------------------------------------------------------------------

export function buildDeskSlots(capacity: number): DeskSlot[] {
  const columns = 4;
  const rows = Math.max(1, Math.ceil(capacity / columns));
  const slots: DeskSlot[] = [];
  const leftStart = 14;
  const leftStep = 22;
  const topStart = 24;
  const topEnd = 68;
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

export function checkDeskCollision(
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

  // Check factory and incinerator collisions
  for (const box of [FACTORY_COLLISION, INCINERATOR_COLLISION]) {
    const bLeft = box.left;
    const bRight = box.left + box.width;
    const bTop = box.top;
    const bBottom = box.top + box.height;
    if (playerRight > bLeft && playerLeft < bRight && playerBottom > bTop && playerTop < bBottom) {
      return true;
    }
  }

  return false;
}

// ---------------------------------------------------------------------------
// Log parsing helpers
// ---------------------------------------------------------------------------

export function accumulateUsage(rawUpdates: string[]): AccumulatedUsage | null {
  let totalCost = 0;
  let totalSeconds = 0;
  let totalIn = 0;
  let totalOut = 0;
  let count = 0;
  for (const entry of rawUpdates) {
    for (const line of String(entry).split(/\r?\n/)) {
      const costMatch = line.match(API_COST_RE);
      if (!costMatch) continue;
      count++;
      totalCost += parseFloat(costMatch[1]);
      const secMatch = line.match(/([0-9]+(?:\.[0-9]+)?)s/);
      if (secMatch) totalSeconds += parseFloat(secMatch[1]);
      const inMatch = line.match(/in=([0-9]+)/);
      if (inMatch) totalIn += parseInt(inMatch[1], 10);
      const outMatch = line.match(/out=([0-9]+)/);
      if (outMatch) totalOut += parseInt(outMatch[1], 10);
    }
  }
  if (count === 0) return null;
  return { totalCost, totalSeconds, totalIn, totalOut, count };
}

export function extractPrefixes(rawUpdates: string[]): string[] {
  const seen = new Set<string>();
  for (const entry of rawUpdates) {
    for (const line of String(entry).split(/\r?\n/)) {
      const m = line.trim().match(PREFIX_RE);
      if (m) {
        seen.add(m[1]);
      }
    }
  }
  return Array.from(seen).sort();
}

export function filterLinesByPrefix(
  text: string,
  filters: Record<string, PrefixFilterMode>
): string {
  const entries = Object.entries(filters);
  if (entries.length === 0) {
    return text;
  }
  const hasOnly = entries.some(([, mode]) => mode === "only");
  const lines = text.split("\n");
  const result: string[] = [];
  for (const line of lines) {
    const m = line.match(PREFIX_RE);
    const prefix = m ? m[1] : null;
    if (hasOnly) {
      if (!prefix || filters[prefix] !== "only") continue;
      result.push(line.replace(PREFIX_RE, "").trimStart());
    } else {
      if (prefix && filters[prefix] === "hide") continue;
      result.push(line);
    }
  }
  return result.join("\n");
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

    if (trimmed.startsWith("[codexcli] still running") || trimmed.startsWith("[claudecodecli] still running") || trimmed.startsWith("[devincli] still running")) {
      pushUnique(trimmed.replace(/^\[(codexcli|claudecodecli|devincli)\] /, ""));
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

    if (trimmed.length <= 250 && !trimmed.startsWith("- ")) {
      pushUnique(trimmed);
    }
  }

  flushIndexedFiles();
  flushGoals();
  return parsed;
}

// ---------------------------------------------------------------------------
// Task history (localStorage)
// ---------------------------------------------------------------------------

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
