import {
  type CSSProperties,
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import HandWorldScene from "./components/HandWorldScene";
import { useMovement } from "./hooks/useMovement";
import { useMultiplayer, loadPlayerName } from "./hooks/useMultiplayer";
import { useSchedules } from "./hooks/useSchedules";
import type {
  AccumulatedUsage,
  Backend,
  BuildResponse,
  ClaudeUsageResponse,
  CurrentTasksResponse,
  DashboardView,
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
  backendDisplayName,
  buildDeskSlots,
  CRON_PRESETS,
  DASHBOARD_VIEW_STORAGE_KEY,
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
  statusBlinkerColor,
  statusTone,
  TASK_HISTORY_STORAGE_KEY,
  upsertTaskHistory,
  wsUrl,
} from "./App.utils";

// Re-export types and utilities so existing imports from "./App" continue to work.
export type { PlayerDirection } from "./types";
export type { AccumulatedUsage, DeskSlot } from "./types";
export {
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
  const [dashboardView, setDashboardView] = useState<DashboardView>("classic");
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
  const [notifPerm, setNotifPerm] = useState<NotificationPermission>(
    typeof Notification !== "undefined" ? Notification.permission : "denied"
  );

  const [playerNameInput, setPlayerNameInput] = useState(loadPlayerName);

  const deskSlots = useMemo(() => buildDeskSlots(maxOfficeWorkers), [maxOfficeWorkers]);

  const {
    playerPosition,
    playerDirection,
    isPlayerWalking,
  } = useMovement({ active: dashboardView === "world", deskSlots });

  const {
    remotePlayers,
    remoteEmotes,
    localEmote,
    connectionStatus: yjsConnStatus,
  } = useMultiplayer({
    active: dashboardView === "world",
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

  const swReg = useRef<ServiceWorkerRegistration | null>(null);

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker
      .register("/notif-sw.js")
      .then((reg) => {
        swReg.current = reg;
        console.log("[HH] Notification SW registered");
      })
      .catch((err) => console.warn("[HH] SW registration failed:", err));
  }, []);

  const sendBrowserNotification = useCallback((notifTaskId: string, notifStatus: string) => {
    if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
    const tone = notifStatus.toUpperCase() === "SUCCESS" ? "completed successfully" : "failed";
    const body = `Task ${shortTaskId(notifTaskId)} ${tone}`;
    const reg = swReg.current;
    if (reg) {
      reg.showNotification("Helping Hands", { body, tag: notifTaskId }).catch((err) =>
        console.error("[HH] showNotification failed:", err)
      );
    } else {
      try { new Notification("Helping Hands", { body }); } catch (_) { /* fallback */ }
    }
  }, []);

  const requestNotifPermission = useCallback(() => {
    if (typeof Notification === "undefined") return;
    Notification.requestPermission().then((perm) => {
      setNotifPerm(perm);
    }).catch(() => { /* permission request failed or was dismissed */ });
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

  const blinkerColor = statusBlinkerColor(status);
  const isBlinkerAnimated = statusTone(status) === "run";

  // Live elapsed-time timer for running tasks; stored runtime for completed tasks.
  const payloadResult = (payload as Record<string, unknown> | null)?.result as Record<string, unknown> | undefined;
  const startedAtRaw = payloadResult?.started_at;
  const storedRuntime = typeof payloadResult?.runtime === "string" ? payloadResult.runtime : null;
  const startedAtMs = useMemo(() => {
    if (typeof startedAtRaw === "string") {
      const ms = Date.parse(startedAtRaw);
      return Number.isFinite(ms) ? ms : null;
    }
    return null;
  }, [startedAtRaw]);

  const [elapsedStr, setElapsedStr] = useState<string | null>(null);

  useEffect(() => {
    if (!startedAtMs || !isBlinkerAnimated) {
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
  }, [startedAtMs, isBlinkerAnimated]);

  const runtimeDisplay = elapsedStr ?? storedRuntime;

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

  const testNotification = () => {
    if (typeof Notification === "undefined") {
      alert("Notification API not available in this context");
      return;
    }
    if (Notification.permission !== "granted") {
      Notification.requestPermission().then((perm) => {
        setNotifPerm(perm);
        if (perm === "granted") testNotification();
      }).catch(() => { /* permission request failed or was dismissed */ });
      return;
    }
    const body = "If you see this, OS notifications are working!";
    const reg = swReg.current;
    if (reg) {
      reg.showNotification("Helping Hands — Test", { body }).catch((err) =>
        alert("showNotification failed: " + String(err))
      );
    } else {
      try { new Notification("Helping Hands — Test", { body }); } catch (err) {
        alert("Notification failed: " + String(err));
      }
    }
  };

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
      <button
        type="button"
        className="service-health-item"
        style={{ cursor: "pointer", background: "none", border: "none", color: "inherit", fontSize: "inherit", padding: 0 }}
        onClick={testNotification}
        title="Send a test OS notification"
      >
        <span className="service-health-label" style={{ textDecoration: "underline", opacity: 0.7 }}>test notification</span>
      </button>
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
            aria-label="Repository path"
          />
          <input
            className="prompt-input"
            value={form.prompt}
            onChange={(event) => updateField("prompt", event.target.value)}
            required
            placeholder="Prompt"
            aria-label="Task prompt"
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
                      {backendDisplayName(backend)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Model
                <input
                  value={form.model}
                  onChange={(event) => updateField("model", event.target.value)}
                  placeholder="claude-opus-4-6"
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
              Tools
              <input
                value={form.tools}
                onChange={(event) => updateField("tools", event.target.value)}
                placeholder="execution,web"
              />
            </label>
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
              <label className="check-row compact-check">
                <input
                  type="checkbox"
                  checked={form.fix_ci}
                  onChange={(event) => updateField("fix_ci", event.target.checked)}
                />
                Fix CI
              </label>
            </div>
            <div className="row">
              <label>
                GitHub Token
                <input
                  type="password"
                  value={form.github_token}
                  onChange={(event) => updateField("github_token", event.target.value)}
                  placeholder="ghp_... (optional)"
                />
              </label>
            </div>
            <div className="row">
              <label>
                Reference Repos
                <input
                  type="text"
                  value={form.reference_repos}
                  onChange={(event) => updateField("reference_repos", event.target.value)}
                  placeholder="owner/repo, owner/repo2 (optional, read-only)"
                />
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
          <h2 className="monitor-title">Output{taskId ? `: ${shortTaskId(taskId)}` : ""}</h2>
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
          {taskId && !isTerminalTaskStatus(status) && (
            <button
              type="button"
              className="secondary cancel-task-btn"
              style={{ fontSize: "0.7rem", padding: "2px 8px", color: "#fca5a5", borderColor: "#7f1d1d" }}
              title="Cancel this task"
              onClick={async () => {
                if (!confirm("Cancel this task?")) return;
                try {
                  await fetch(apiUrl(`/tasks/${taskId}/cancel`), { method: "POST" });
                } catch {
                  /* swallow — next poll picks up REVOKED */
                }
              }}
            >
              Cancel
            </button>
          )}
          <button
            type="button"
            className="secondary"
            style={{ fontSize: "0.7rem", padding: "2px 8px" }}
            title="Copy output to clipboard"
            onClick={() => {
              navigator.clipboard.writeText(activeOutputText).catch(() => {});
            }}
          >
            Copy
          </button>
          <span
            className={`status-blinker${isBlinkerAnimated ? " pulse" : ""}`}
            style={{ backgroundColor: blinkerColor }}
            title={`${status}${isPolling ? " (polling)" : ""}`}
          />
          {runtimeDisplay && (
            <span className="elapsed-timer" title="Elapsed runtime">
              {runtimeDisplay}
            </span>
          )}
          <span className="info-badge" title={taskId || "No task selected"}>
            i
          </span>
        </div>
      </div>
      {(accUsage || (detectedPrefixes.length > 0 && outputTab !== "payload")) && (
        <div className="prefix-filters">
          {detectedPrefixes.length > 0 && outputTab !== "payload" && (
            <>
              <span className="prefix-filters-label">Filter:</span>
              {detectedPrefixes.map((prefix) => {
                const mode = prefixFilters[prefix] ?? "show";
                return (
                  <button
                    key={prefix}
                    type="button"
                    className={`prefix-chip ${mode}`}
                    title={`[${prefix}] — ${mode === "show" ? "Showing (click to hide)" : mode === "hide" ? "Hidden (click for only)" : "Only (click to reset)"}`}
                    onClick={() => {
                      setPrefixFilters((prev) => {
                        const current = prev[prefix] ?? "show";
                        const next: PrefixFilterMode =
                          current === "show" ? "hide" : current === "hide" ? "only" : "show";
                        const updated = { ...prev };
                        if (next === "show") {
                          delete updated[prefix];
                        } else {
                          updated[prefix] = next;
                        }
                        return updated;
                      });
                    }}
                  >
                    <span className="prefix-chip-icon">
                      {mode === "show" ? "●" : mode === "hide" ? "○" : "◉"}
                    </span>
                    [{prefix}]
                  </button>
                );
              })}
              {Object.keys(prefixFilters).length > 0 && (
                <button
                  type="button"
                  className="prefix-chip reset"
                  title="Reset all filters"
                  onClick={() => setPrefixFilters({})}
                >
                  Reset
                </button>
              )}
            </>
          )}
          {accUsage && (
            <span
              className="usage-total"
              title={`${accUsage.count} API call${accUsage.count !== 1 ? "s" : ""}, ${Math.round(accUsage.totalSeconds)}s, in=${accUsage.totalIn.toLocaleString()} out=${accUsage.totalOut.toLocaleString()}`}
            >
              api: ${accUsage.totalCost.toFixed(4)}, {Math.round(accUsage.totalSeconds)}s, in={accUsage.totalIn.toLocaleString()} out={accUsage.totalOut.toLocaleString()}
            </span>
          )}
        </div>
      )}
      <pre
        ref={monitorOutputRef}
        className="monitor-output"
        onScroll={handleMonitorScroll}
        style={monitorHeight != null ? { height: monitorHeight, minHeight: 60, maxHeight: "none" } : undefined}
      >{activeOutputText}</pre>
      <div className="monitor-resize-handle" onMouseDown={handleResizeStart} title="Drag to resize" />

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

  const scheduleFormFields = (
    <form onSubmit={saveSchedule} className="form-grid" style={{ marginTop: 0 }}>
      <label>
        Name
        <input
          value={scheduleForm.name}
          onChange={(e) => updateScheduleField("name", e.target.value)}
          required
          placeholder="e.g. Daily docs update"
        />
      </label>

      <div className="row two-col">
        <label>
          Cron expression
          <input
            value={scheduleForm.cron_expression}
            onChange={(e) => updateScheduleField("cron_expression", e.target.value)}
            required
            placeholder="0 0 * * * (midnight)"
          />
        </label>
        <label>
          Or preset
          <select
            value={
              Object.entries(CRON_PRESETS).find(
                ([, v]) => v === scheduleForm.cron_expression,
              )?.[0] ?? ""
            }
            onChange={(e) => {
              const preset = e.target.value;
              if (preset && CRON_PRESETS[preset]) {
                updateScheduleField("cron_expression", CRON_PRESETS[preset]);
              }
            }}
          >
            <option value="">Custom</option>
            {Object.entries(CRON_PRESETS).map(([key, val]) => (
              <option key={key} value={key}>
                {key.replace(/_/g, " ")} ({val})
              </option>
            ))}
          </select>
        </label>
      </div>

      <label>
        Repo path (owner/repo)
        <input
          value={scheduleForm.repo_path}
          onChange={(e) => updateScheduleField("repo_path", e.target.value)}
          required
          placeholder="owner/repo"
        />
      </label>

      <label>
        Prompt
        <textarea
          value={scheduleForm.prompt}
          onChange={(e) => updateScheduleField("prompt", e.target.value)}
          required
          rows={4}
          placeholder="Update documentation..."
        />
      </label>

      <details className="advanced-settings">
        <summary>Advanced settings</summary>
        <div className="advanced-settings-body">
          <div className="row two-col">
            <label>
              Backend
              <select
                value={scheduleForm.backend}
                onChange={(e) => updateScheduleField("backend", e.target.value as Backend)}
              >
                {BACKEND_OPTIONS.map((b) => (
                  <option key={b} value={b}>{backendDisplayName(b)}</option>
                ))}
              </select>
            </label>
            <label>
              Model
              <input
                value={scheduleForm.model}
                onChange={(e) => updateScheduleField("model", e.target.value)}
                placeholder="claude-opus-4-6"
              />
            </label>
          </div>
          <div className="row two-col">
            <label>
              Max iterations
              <input
                type="number"
                min={1}
                value={scheduleForm.max_iterations}
                onChange={(e) =>
                  updateScheduleField("max_iterations", Math.max(1, Number(e.target.value || 1)))
                }
              />
            </label>
            <label>
              PR number
              <input
                type="number"
                min={1}
                value={scheduleForm.pr_number}
                onChange={(e) => updateScheduleField("pr_number", e.target.value)}
              />
            </label>
          </div>
          <label>
            Tools
            <input
              value={scheduleForm.tools}
              onChange={(e) => updateScheduleField("tools", e.target.value)}
              placeholder="execution,web"
            />
          </label>
          <label>
            Skills
            <input
              value={scheduleForm.skills}
              onChange={(e) => updateScheduleField("skills", e.target.value)}
              placeholder="execution,web,prd"
            />
          </label>
          <div className="row check-grid">
            <label className="check-row">
              <input
                type="checkbox"
                checked={scheduleForm.no_pr}
                onChange={(e) => updateScheduleField("no_pr", e.target.checked)}
              />
              No PR
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={scheduleForm.enable_execution}
                onChange={(e) => updateScheduleField("enable_execution", e.target.checked)}
              />
              Execution
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={scheduleForm.enable_web}
                onChange={(e) => updateScheduleField("enable_web", e.target.checked)}
              />
              Web
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={scheduleForm.use_native_cli_auth}
                onChange={(e) => updateScheduleField("use_native_cli_auth", e.target.checked)}
              />
              Native auth
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={scheduleForm.fix_ci}
                onChange={(e) => updateScheduleField("fix_ci", e.target.checked)}
              />
              Fix CI
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={scheduleForm.enabled}
                onChange={(e) => updateScheduleField("enabled", e.target.checked)}
              />
              Enabled
            </label>
          </div>
          <div className="row">
            <label>
              GitHub Token
              <input
                type="password"
                value={scheduleForm.github_token}
                onChange={(e) => updateScheduleField("github_token", e.target.value)}
                placeholder="ghp_... (optional)"
              />
            </label>
          </div>
          <div className="row">
            <label>
              Reference Repos
              <input
                type="text"
                value={scheduleForm.reference_repos}
                onChange={(e) => updateScheduleField("reference_repos", e.target.value)}
                placeholder="owner/repo, owner/repo2 (optional, read-only)"
              />
            </label>
          </div>
        </div>
      </details>

      <div style={{ display: "flex", gap: 8 }}>
        <button type="submit">
          {editingScheduleId ? "Update schedule" : "Create schedule"}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={cancelScheduleForm}
        >
          Cancel
        </button>
      </div>
    </form>
  );

  const schedulesCard = (
    <section className="card compact-form" style={{ padding: "14px 16px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>
            Scheduled tasks{" "}
            <span className="status-pill run" style={{ fontSize: "0.6rem", verticalAlign: "middle" }}>
              cron
            </span>
          </h2>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: "0.84rem" }}>
            Create and manage recurring builds.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button type="button" onClick={openNewScheduleForm}>
            New schedule
          </button>
          <button type="button" className="secondary" onClick={() => void loadSchedules()}>
            Refresh
          </button>
        </div>
      </div>

      {scheduleError && (
        <div style={{ padding: "8px 10px", marginBottom: 10, borderRadius: 8, background: "var(--danger-soft)", border: "1px solid var(--danger)", color: "#fca5a5", fontSize: "0.84rem" }}>
          {scheduleError}
        </div>
      )}

      {showScheduleForm && !editingScheduleId && (
        <div style={{ marginBottom: 14, paddingBottom: 14, borderBottom: "1px solid var(--border)" }}>
          <h3 style={{ margin: "0 0 10px", fontSize: "0.95rem" }}>New schedule</h3>
          {scheduleFormFields}
        </div>
      )}

      {schedules.length === 0 && !showScheduleForm ? (
        <p className="empty-list">No scheduled tasks yet.</p>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {schedules.map((item) => (
            <div key={item.schedule_id} className="schedule-item">
              {editingScheduleId === item.schedule_id ? (
                <div style={{ padding: "4px 0" }}>
                  {scheduleFormFields}
                </div>
              ) : (
                <>
                  <div className="schedule-item-header">
                    <strong>{item.name}</strong>
                    <span className={`status-pill ${item.enabled ? "ok" : "idle"}`}>
                      {item.enabled ? "enabled" : "disabled"}
                    </span>
                  </div>
                  <div className="schedule-item-meta">
                    <code>{item.cron_expression}</code> &middot; {item.repo_path} &middot;{" "}
                    {item.backend}
                    {item.next_run_at && (
                      <> &middot; next: {new Date(item.next_run_at).toLocaleString()}</>
                    )}
                  </div>
                  <div className="schedule-item-meta" style={{ fontSize: "0.72rem" }}>
                    {item.run_count} runs
                    {item.last_run_at && (
                      <> &middot; last: {new Date(item.last_run_at).toLocaleString()}</>
                    )}
                  </div>
                  <div className="schedule-item-actions">
                    <button
                      type="button"
                      className="secondary"
                      style={{ padding: "5px 10px", fontSize: "0.76rem" }}
                      onClick={() => void openEditScheduleForm(item.schedule_id)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      style={{ padding: "5px 10px", fontSize: "0.76rem" }}
                      onClick={() => void triggerSchedule(item.schedule_id)}
                    >
                      Run now
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      style={{ padding: "5px 10px", fontSize: "0.76rem" }}
                      onClick={() => void toggleSchedule(item.schedule_id, !item.enabled)}
                    >
                      {item.enabled ? "Disable" : "Enable"}
                    </button>
                    <button
                      type="button"
                      style={{
                        padding: "5px 10px",
                        fontSize: "0.76rem",
                        background: "var(--danger-soft)",
                        border: "1px solid var(--danger)",
                        color: "#fca5a5",
                      }}
                      onClick={() => void deleteSchedule(item.schedule_id)}
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
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
        <button
          type="button"
          className={`new-submission-button${
            mainView === "schedules" ? " active" : ""
          }`}
          style={{ marginTop: 0 }}
          onClick={() => setMainView("schedules")}
        >
          Scheduled tasks
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
          ) : mainView === "schedules" ? (
            schedulesCard
          ) : (
            monitorCard
          )
        ) : (
          <>
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
              connectionStatus={yjsConnStatus}
              playerNameInput={playerNameInput}
              onPlayerNameChange={setPlayerNameInput}
              claudeUsage={claudeUsage}
              claudeUsageLoading={claudeUsageLoading}
              onRefreshClaudeUsage={() => void refreshClaudeUsage()}
              floatingNumbers={floatingNumbers}
            />

            {mainView !== "schedules" && submissionCard}
            {mainView === "monitor" && taskId && monitorCard}
            {mainView === "schedules" && schedulesCard}
          </>
        )}
      </div>
    </main>
    {notifPerm === "default" && (
      <div className="notif-banner">
        <span>Enable OS notifications for task updates?</span>
        <button onClick={requestNotifPermission}>Enable</button>
        <button onClick={() => setNotifPerm("denied")}>Dismiss</button>
      </div>
    )}
    {toasts.length > 0 && (
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast--${statusTone(t.status)}`}>
            <span className="toast-text">
              Task {shortTaskId(t.taskId)} — {t.status}
            </span>
            <button className="toast-close" onClick={() => removeToast(t.id)} aria-label="Dismiss">
              ×
            </button>
          </div>
        ))}
      </div>
    )}
    {serviceHealthBar}
    </>
  );
}
