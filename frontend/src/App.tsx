import {
  type CSSProperties,
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import AppOverlays from "./components/AppOverlays";
import HandWorldScene from "./components/HandWorldScene";
import MonitorCard from "./components/MonitorCard";
import ScheduleCard from "./components/ScheduleCard";
import SubmissionForm from "./components/SubmissionForm";
import TaskListSidebar from "./components/TaskListSidebar";
import { useMovement } from "./hooks/useMovement";
import { useMultiplayer, loadPlayerName } from "./hooks/useMultiplayer";
import { useSchedules } from "./hooks/useSchedules";
import type {
  AccumulatedUsage,
  Backend,
  BuildResponse,
  ClaudeUsageResponse,
  CurrentTasksResponse,
  FloatingNumber,
  FormState,
  InputItem,
  MainView,
  OutputTab,
  PrefixFilterMode,
  ScheduleItem,
  SceneWorker,
  SceneWorkerPhase,
  ServiceHealthState,
  TaskHistoryItem,
  TaskHistoryPatch,
  TaskStatus,
  WorkerVariant,
} from "./types";
import {
  accumulateUsage,
  apiUrl,
  asRecord,
  BACKEND_OPTIONS,
  buildDeskSlots,
  DEFAULT_CHARACTER_STYLE,
  DEFAULT_WORLD_MAX_WORKERS,
  extractPrefixes,
  extractUpdates,
  fetchClaudeUsage,
  fetchServerConfig,
  fetchServiceHealth,
  fetchWorkerCapacity,
  filterLinesByPrefix,
  INITIAL_FORM,
  isTerminalTaskStatus,
  loadTaskHistory,
  parseBool,
  parseError,
  parseOptimisticUpdates,
  PHASE_DURATION,
  providerFromBackend,
  PROVIDER_CHARACTER_DEFAULTS,
  readBoolishValue,
  readSkillsValue,
  readStringValue,
  shortTaskId,
  statusTone,
  TASK_HISTORY_STORAGE_KEY,
  upsertTaskHistory,
  wsUrl,
} from "./App.utils";

// Re-export types and utilities so existing imports from "./App" continue to work.
export type { PlayerDirection } from "./types";
export type { AccumulatedUsage, DeskSlot } from "./types";
export {
  CHAT_DISPLAY_MS,
  CHAT_MAX_LENGTH,
  EMOTE_DISPLAY_MS,
  EMOTE_KEY_BINDINGS,
  EMOTE_MAP,
  PLAYER_COLORS,
  FACTORY_POS,
  INCINERATOR_POS,
  PLAYER_MOVE_STEP,
  PLAYER_SIZE,
  DESK_SIZE,
  FACTORY_COLLISION,
  INCINERATOR_COLLISION,
  OFFICE_BOUNDS,
} from "./constants";
export {
  accumulateUsage,
  apiUrl,
  asRecord,
  backendDisplayName,
  buildDeskSlots,
  checkDeskCollision,
  cronFrequency,
  extractPrefixes,
  extractUpdates,
  filterLinesByPrefix,
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
  statusBlinkerColor,
  statusTone,
  TASK_HISTORY_STORAGE_KEY,
  upsertTaskHistory,
  wsUrl,
} from "./App.utils";

export default function App() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState("idle");
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [updates, setUpdates] = useState<string[]>([]);
  const [outputTab, setOutputTab] = useState<OutputTab>("updates");
  const [prefixFilters, setPrefixFilters] = useState<Record<string, PrefixFilterMode>>({});
  const [mainView, setMainView] = useState<MainView>("submission");
  const [isPolling, setIsPolling] = useState(false);
  const [taskHistory, setTaskHistory] = useState<TaskHistoryItem[]>([]);
  const [showSubmissionOverlay, setShowSubmissionOverlay] = useState(false);
  const [sceneWorkers, setSceneWorkers] = useState<SceneWorker[]>([]);
  const [maxOfficeWorkers, setMaxOfficeWorkers] = useState(DEFAULT_WORLD_MAX_WORKERS);
  const slotByTaskRef = useRef<Record<string, number>>({});
  const sceneRef = useRef<HTMLDivElement>(null);
  const [serviceHealthState, setServiceHealthState] = useState<ServiceHealthState | null>(null);
  const {
    schedules,
    scheduleForm,
    editingScheduleId,
    showScheduleForm,
    scheduleError,
    updateScheduleField,
    loadSchedules,
    openNewScheduleForm,
    openEditScheduleForm,
    saveSchedule,
    deleteSchedule,
    triggerSchedule,
    toggleSchedule,
    cancelScheduleForm,
  } = useSchedules();
  const [floatingNumbers, setFloatingNumbers] = useState<FloatingNumber[]>([]);
  const floatingIdRef = useRef(0);
  const updateCountsRef = useRef<Map<string, number>>(new Map());
  const [toasts, setToasts] = useState<{ id: number; taskId: string; status: string }[]>([]);
  const toastIdRef = useRef(0);
  const [playerNameInput, setPlayerNameInput] = useState(loadPlayerName);

  const deskSlots = useMemo(() => buildDeskSlots(maxOfficeWorkers), [maxOfficeWorkers]);

  const {
    playerPosition,
    playerDirection,
    isPlayerWalking,
  } = useMovement({ active: true, deskSlots });

  const {
    remotePlayers,
    remoteEmotes,
    remoteChats,
    remoteTyping,
    localEmote,
    localChat,
    isLocalIdle,
    isLocalTyping,
    connectionStatus: yjsConnStatus,
    chatHistory,
    sendChat,
    setTyping,
  } = useMultiplayer({
    active: true,
    playerPosition,
    playerDirection,
    isPlayerWalking,
    wsUrlBuilder: wsUrl,
    playerName: playerNameInput,
  });

  const [claudeUsage, setClaudeUsage] = useState<ClaudeUsageResponse | null>(null);
  const [claudeUsageLoading, setClaudeUsageLoading] = useState(false);

  const monitorOutputRef = useRef<HTMLPreElement>(null);
  const autoScrollRef = useRef(true);
  const [monitorHeight, setMonitorHeight] = useState<number | null>(null);

  const spawnFloatingNumber = useCallback((forTaskId: string, delta: number) => {
    if (delta <= 0) return;
    const id = ++floatingIdRef.current;
    const now = Date.now();
    setFloatingNumbers((prev) => [...prev, { id, taskId: forTaskId, value: delta, createdAt: now }]);
    setTimeout(() => {
      setFloatingNumbers((prev) => prev.filter((f) => f.id !== id));
    }, 1200);
  }, []);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((toastTaskId: string, toastStatus: string) => {
    const id = ++toastIdRef.current;
    setToasts((prev) => [...prev, { id, taskId: toastTaskId, status: toastStatus }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const sendBrowserNotification = useCallback((notifTaskId: string, notifStatus: string) => {
    if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
    const tone = notifStatus.toUpperCase() === "SUCCESS" ? "completed successfully" : "failed";
    const body = `Task ${shortTaskId(notifTaskId)} ${tone}`;
    try { new Notification("Helping Hands", { body }); } catch (_) { /* fallback */ }
  }, []);

  const handleMonitorScroll = useCallback(() => {
    const el = monitorOutputRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 8;
    autoScrollRef.current = atBottom;
  }, []);

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const el = monitorOutputRef.current;
    if (!el) return;
    const startY = e.clientY;
    const startH = el.getBoundingClientRect().height;
    const onMove = (ev: MouseEvent) => {
      const newH = Math.max(60, startH + ev.clientY - startY);
      setMonitorHeight(newH);
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, []);

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

  const detectedPrefixes = useMemo(() => extractPrefixes(updates), [updates]);

  const [accUsage, setAccUsage] = useState<AccumulatedUsage | null>(null);
  const accUsageCursorRef = useRef(0);

  useEffect(() => {
    const payloadUpdates = extractUpdates(
      (payload as Record<string, unknown> | null)?.result as Record<string, unknown> | null
    );
    const cursor = accUsageCursorRef.current;
    if (payloadUpdates.length < cursor) {
      // updates were reset (task switch, new submission) — start fresh
      accUsageCursorRef.current = 0;
      setAccUsage(null);
      if (payloadUpdates.length > 0) {
        const fresh = accumulateUsage(payloadUpdates);
        accUsageCursorRef.current = payloadUpdates.length;
        setAccUsage(fresh);
      }
      return;
    }
    if (payloadUpdates.length === cursor) return;
    // scan only new entries
    const newEntries = payloadUpdates.slice(cursor);
    accUsageCursorRef.current = payloadUpdates.length;
    const delta = accumulateUsage(newEntries);
    if (!delta) return;
    setAccUsage((prev) => {
      if (!prev) return delta;
      return {
        totalCost: prev.totalCost + delta.totalCost,
        totalSeconds: prev.totalSeconds + delta.totalSeconds,
        totalIn: prev.totalIn + delta.totalIn,
        totalOut: prev.totalOut + delta.totalOut,
        count: prev.count + delta.count,
      };
    });
  }, [payload]);

  const activeOutputText = useMemo(() => {
    let text: string;
    if (outputTab === "raw") {
      text = rawUpdatesText;
    } else if (outputTab === "payload") {
      text = payloadText;
    } else {
      text = optimisticUpdatesText;
    }
    if (outputTab !== "payload") {
      text = filterLinesByPrefix(text, prefixFilters);
    }
    return text;
  }, [optimisticUpdatesText, outputTab, payloadText, rawUpdatesText, prefixFilters]);

  useEffect(() => {
    const el = monitorOutputRef.current;
    if (el && autoScrollRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [activeOutputText]);

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

  const scheduleByTaskId = useMemo(() => {
    const map = new Map<string, ScheduleItem>();
    for (const s of schedules) {
      if (s.last_run_task_id) {
        map.set(s.last_run_task_id, s);
      }
    }
    return map;
  }, [schedules]);

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
          schedule: scheduleByTaskId.get(worker.taskId) ?? null,
        },
      ];
    });
  }, [activeTaskIds, deskSlots, scheduleByTaskId, sceneWorkers, taskById]);

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
    const fixCi = readBoolish(["fix_ci"]);
    const tools = readSkills(["tools"]);
    const skills = readSkills(["skills"]);
    const runtime = readString(["runtime"]);
    const referenceRepos = readSkills(["reference_repos"]);

    if (repoPath) {
      items.push({ label: "Repo", value: repoPath });
    }
    if (prompt) {
      items.push({ label: "Prompt", value: prompt });
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
    if (fixCi) {
      items.push({ label: "Fix CI", value: fixCi });
    }
    if (tools) {
      items.push({ label: "Tools", value: tools });
    }
    if (skills) {
      items.push({ label: "Skills", value: skills });
    }
    if (referenceRepos) {
      items.push({ label: "Reference repos", value: referenceRepos });
    }
    if (runtime) {
      items.push({ label: "Runtime", value: runtime });
    }

    return items;
  }, [payload, selectedTask]);

  useEffect(() => {
    setTaskHistory(loadTaskHistory());
  }, []);


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
            phase: "at-factory",
            phaseChangedAt: now,
          });
          continue;
        }
        if (existing.phase === "walking-to-exit" || existing.phase === "at-exit") {
          next.push({
            ...existing,
            slot,
            phase: "at-factory",
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
        if (existing.phase === "walking-to-exit" || existing.phase === "at-exit") {
          next.push(existing);
          continue;
        }
        next.push({
          ...existing,
          phase: "walking-to-exit",
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

    const NEXT_PHASE: Partial<Record<SceneWorkerPhase, SceneWorkerPhase | null>> = {
      "at-factory": "walking-to-desk",
      "walking-to-desk": "active",
      "walking-to-exit": "at-exit",
      "at-exit": null,
    };

    const handle = window.setInterval(() => {
      const now = Date.now();
      setSceneWorkers((current) => {
        let hasChanges = false;
        const next: SceneWorker[] = [];

        for (const worker of current) {
          const elapsed = now - worker.phaseChangedAt;
          const duration = PHASE_DURATION[worker.phase];
          if (duration !== Infinity && elapsed >= duration) {
            const nextPhase = NEXT_PHASE[worker.phase];
            if (nextPhase === null || nextPhase === undefined) {
              delete slotByTaskRef.current[worker.taskId];
              hasChanges = true;
              continue;
            }
            next.push({
              ...worker,
              phase: nextPhase,
              phaseChangedAt: now,
            });
            hasChanges = true;
            continue;
          }
          next.push(worker);
        }

        return hasChanges ? next : current;
      });
    }, 100);

    return () => {
      window.clearInterval(handle);
    };
  }, [sceneWorkers.length]);

  // Player movement is handled by useMovement (keyboard input, collision, clamping).

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

      const tools = params.get("tools");
      if (tools) {
        next.tools = tools;
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
      const fixCiParam = params.get("fix_ci");
      if (fixCiParam !== null) {
        next.fix_ci = parseBool(fixCiParam);
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

  // Claude Code usage polling — refresh every hour
  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      const data = await fetchClaudeUsage();
      if (!cancelled) {
        setClaudeUsage(data);
      }
    };
    void refresh();
    const handle = window.setInterval(() => void refresh(), 3_600_000);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  const refreshClaudeUsage = useCallback(async () => {
    setClaudeUsageLoading(true);
    const data = await fetchClaudeUsage(true);
    setClaudeUsage(data);
    setClaudeUsageLoading(false);
  }, []);

  useEffect(() => {
    if (mainView === "schedules") {
      void loadSchedules();
    }
  }, [mainView, loadSchedules]);

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
    }).catch(() => { /* server config fetch is best-effort */ });
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
        const freshUpdates = extractUpdates(data.result);
        setUpdates(freshUpdates);
        {
          const prev = updateCountsRef.current.get(data.task_id) ?? 0;
          const curr = freshUpdates.length;
          if (curr > prev) {
            spawnFloatingNumber(data.task_id, curr - prev);
          }
          updateCountsRef.current.set(data.task_id, curr);
        }
        setTaskHistory((current) =>
          upsertTaskHistory(current, {
            taskId: data.task_id,
            status: data.status,
          })
        );

        if (isTerminalTaskStatus(data.status)) {
          addToast(data.task_id, data.status);
          sendBrowserNotification(data.task_id, data.status);
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
  }, [isPolling, taskId, spawnFloatingNumber, addToast, sendBrowserNotification]);

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

            const bgUpdates = extractUpdates(data.result);
            const prev = updateCountsRef.current.get(data.task_id) ?? 0;
            if (bgUpdates.length > prev) {
              spawnFloatingNumber(data.task_id, bgUpdates.length - prev);
              updateCountsRef.current.set(data.task_id, bgUpdates.length);
            }

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
          const prev = current.find((h) => h.taskId === patch.taskId);
          if (
            patch.status &&
            isTerminalTaskStatus(patch.status) &&
            (!prev || !isTerminalTaskStatus(prev.status))
          ) {
            addToast(patch.taskId, patch.status);
            sendBrowserNotification(patch.taskId, patch.status);
          }
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
  }, [isPolling, taskHistory, taskId, spawnFloatingNumber, addToast, sendBrowserNotification]);

  const updateField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const openSubmissionView = () => {
    setShowSubmissionOverlay(true);
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
    autoScrollRef.current = true;
    setTaskHistory((current) =>
      upsertTaskHistory(current, {
        taskId: selectedTaskId,
        status: "monitoring",
      })
    );
  };

  const submitRun = async (event: FormEvent) => {
    event.preventDefault();

    const repoPath = form.repo_path.trim();
    const prompt = form.prompt.trim();
    if (!repoPath || !prompt) {
      setStatus("error");
      setPayload({ error: "Repository path and prompt are required." });
      setUpdates(["Error: Repository path and prompt are required."]);
      return;
    }

    setStatus("submitting");
    setShowSubmissionOverlay(false);
    setMainView("monitor");
    setPayload(null);
    setUpdates([]);
    const body: Record<string, unknown> = {
      repo_path: repoPath,
      prompt,
      backend: form.backend,
      max_iterations: form.max_iterations,
      no_pr: form.no_pr,
      enable_execution: form.enable_execution,
      enable_web: form.enable_web,
      use_native_cli_auth: form.use_native_cli_auth,
      fix_ci: form.fix_ci,
      ci_check_wait_minutes: form.ci_check_wait_minutes,
    };

    if (form.github_token.trim()) {
      body.github_token = form.github_token.trim();
    }
    if (form.reference_repos.trim()) {
      body.reference_repos = form.reference_repos.split(",").map((s: string) => s.trim()).filter((s: string) => s.length > 0);
    }
    if (form.model.trim()) {
      body.model = form.model.trim();
    }
    if (form.pr_number.trim()) {
      const parsed = Number(form.pr_number.trim());
      if (!Number.isNaN(parsed) && Number.isFinite(parsed)) {
        body.pr_number = parsed;
      }
    }
    if (form.tools.trim()) {
      body.tools = form.tools
        .split(",")
        .map((item) => item.trim())
        .filter((item) => item.length > 0);
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

  // Live elapsed-time timer for running tasks; stored runtime for completed tasks.
  const payloadResult = (payload as Record<string, unknown> | null)?.result as Record<string, unknown> | undefined;
  const startedAtRaw = payloadResult?.started_at;
  const storedRuntime = typeof payloadResult?.runtime === "string" ? payloadResult.runtime : null;
  const isTaskRunning = statusTone(status) === "run";
  const startedAtMs = useMemo(() => {
    if (typeof startedAtRaw === "string") {
      const ms = Date.parse(startedAtRaw);
      return Number.isFinite(ms) ? ms : null;
    }
    return null;
  }, [startedAtRaw]);

  const [elapsedStr, setElapsedStr] = useState<string | null>(null);

  useEffect(() => {
    if (!startedAtMs || !isTaskRunning) {
      setElapsedStr(null);
      return;
    }
    const tick = () => {
      const totalSec = Math.max(0, Math.floor((Date.now() - startedAtMs) / 1000));
      const m = Math.floor(totalSec / 60);
      const s = totalSec % 60;
      setElapsedStr(m > 0 ? `${m}m ${s.toString().padStart(2, "0")}s` : `${s}s`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startedAtMs, isTaskRunning]);

  const runtimeDisplay = elapsedStr ?? storedRuntime;

  const submissionCard = (
    <SubmissionForm form={form} onFieldChange={updateField} onSubmit={submitRun} />
  );

  const monitorCard = (
    <MonitorCard
      taskId={taskId}
      status={status}
      isPolling={isPolling}
      outputTab={outputTab}
      onOutputTabChange={setOutputTab}
      prefixFilters={prefixFilters}
      onPrefixFiltersChange={setPrefixFilters}
      activeOutputText={activeOutputText}
      detectedPrefixes={detectedPrefixes}
      accUsage={accUsage}
      taskInputs={taskInputs}
      runtimeDisplay={runtimeDisplay}
      monitorOutputRef={monitorOutputRef}
      monitorHeight={monitorHeight}
      onMonitorScroll={handleMonitorScroll}
      onResizeStart={handleResizeStart}
    />
  );

  const schedulesCard = (
    <ScheduleCard
      schedules={schedules}
      scheduleForm={scheduleForm}
      editingScheduleId={editingScheduleId}
      showScheduleForm={showScheduleForm}
      scheduleError={scheduleError}
      onUpdateField={updateScheduleField}
      onNewSchedule={openNewScheduleForm}
      onEditSchedule={openEditScheduleForm}
      onSaveSchedule={saveSchedule}
      onDeleteSchedule={deleteSchedule}
      onTriggerSchedule={triggerSchedule}
      onToggleSchedule={toggleSchedule}
      onCancelForm={cancelScheduleForm}
      onRefresh={loadSchedules}
    />
  );

  return (
    <>
    <main className="page">
      <TaskListSidebar
        mainView={mainView}
        showSubmissionOverlay={showSubmissionOverlay}
        onNewSubmission={openSubmissionView}
        onToggleSchedules={() => setMainView(v => v === "schedules" ? "submission" : "schedules")}
        taskHistory={taskHistory}
        selectedTaskId={taskId}
        onSelectTask={selectTask}
        onClearHistory={() => setTaskHistory([])}
      />

      <div className="main-column">
        <HandWorldScene
          sceneRef={sceneRef}
          sceneStyle={worldSceneStyle}
          maxWorkers={maxOfficeWorkers}
          deskSlots={deskSlots}
          workerEntries={sceneWorkerEntries}
          selectedTaskId={taskId}
          onSelectTask={selectTask}
          playerDirection={playerDirection}
          isPlayerWalking={isPlayerWalking}
          playerPosition={playerPosition}
          localEmote={localEmote}
          remotePlayers={remotePlayers}
          remoteEmotes={remoteEmotes}
          remoteChats={remoteChats}
          remoteTyping={remoteTyping}
          localChat={localChat}
          isLocalIdle={isLocalIdle}
          isLocalTyping={isLocalTyping}
          connectionStatus={yjsConnStatus}
          chatHistory={chatHistory}
          onSendChat={sendChat}
          onSetTyping={setTyping}
          playerNameInput={playerNameInput}
          onPlayerNameChange={setPlayerNameInput}
          claudeUsage={claudeUsage}
          claudeUsageLoading={claudeUsageLoading}
          onRefreshClaudeUsage={() => void refreshClaudeUsage()}
          floatingNumbers={floatingNumbers}
        />

        {mainView === "monitor" && taskId && monitorCard}
        {mainView === "schedules" && schedulesCard}
      </div>

      {showSubmissionOverlay && (
        <div className="submission-overlay" onClick={() => setShowSubmissionOverlay(false)}>
          <div className="submission-overlay-content" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="submission-overlay-close"
              onClick={() => setShowSubmissionOverlay(false)}
              aria-label="Close"
            >
              ×
            </button>
            {submissionCard}
          </div>
        </div>
      )}
    </main>
    <AppOverlays
      serviceHealthState={serviceHealthState}
      toasts={toasts}
      onRemoveToast={removeToast}
    />
    </>
  );
}
