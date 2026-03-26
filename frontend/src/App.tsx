import {
  type CSSProperties,
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
import { useMultiplayer, loadPlayerName, loadPlayerColor } from "./hooks/useMultiplayer";
import { useSchedules } from "./hooks/useSchedules";
import { useTaskManager } from "./hooks/useTaskManager";
import type {
  ClaudeUsageResponse,
  SceneWorker,
  SceneWorkerPhase,
  ServiceHealthState,
  WorkerVariant,
} from "./types";
import {
  buildDeskSlots,
  DEFAULT_CHARACTER_STYLE,
  DEFAULT_WORLD_MAX_WORKERS,
  fetchClaudeUsage,
  fetchServerConfig,
  fetchServiceHealth,
  PHASE_DURATION,
  providerFromBackend,
  PROVIDER_CHARACTER_DEFAULTS,
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
  const {
    form,
    updateField,
    setForm,
    taskId,
    status,
    isPolling,
    outputTab,
    setOutputTab,
    prefixFilters,
    setPrefixFilters,
    mainView,
    setMainView,
    showSubmissionOverlay,
    setShowSubmissionOverlay,
    taskHistory,
    setTaskHistory,
    activeTasks,
    activeTaskIds,
    taskById,
    activeOutputText,
    detectedPrefixes,
    accUsage,
    taskInputs,
    runtimeDisplay,
    monitorOutputRef,
    monitorHeight,
    handleMonitorScroll,
    handleResizeStart,
    floatingNumbers,
    toasts,
    removeToast,
    fetchedCapacity,
    submitRun,
    selectTask,
    openSubmissionView,
  } = useTaskManager();

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
  const [playerNameInput, setPlayerNameInput] = useState(loadPlayerName);
  const [playerColorInput, setPlayerColorInput] = useState(loadPlayerColor);

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
    triggerEmote,
    sendChat,
    setTyping,
    chatOnCooldown,
    decorations,
    placeDecoration,
    clearDecorations,
  } = useMultiplayer({
    active: true,
    playerPosition,
    playerDirection,
    isPlayerWalking,
    wsUrlBuilder: wsUrl,
    playerName: playerNameInput,
    playerColor: playerColorInput,
  });

  const [claudeUsage, setClaudeUsage] = useState<ClaudeUsageResponse | null>(null);
  const [claudeUsageLoading, setClaudeUsageLoading] = useState(false);

  const scheduleByTaskId = useMemo(() => {
    const map = new Map<string, (typeof schedules)[number]>();
    for (const s of schedules) {
      if (s.last_run_task_id) {
        map.set(s.last_run_task_id, s);
      }
    }
    return map;
  }, [schedules]);

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
      if (!task || !desk) return [];

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
    return { minHeight: `${380 + extraRows * 92}px` };
  }, [officeDeskRows]);

  // -- Capacity → max workers -----------------------------------------------
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

  // -- Scene worker lifecycle -----------------------------------------------
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
          next.push({ taskId: task.taskId, slot, phase: "at-factory", phaseChangedAt: now });
          continue;
        }
        if (existing.phase === "walking-to-exit" || existing.phase === "at-exit") {
          next.push({ ...existing, slot, phase: "at-factory", phaseChangedAt: now });
          continue;
        }
        if (existing.slot !== slot) {
          next.push({ ...existing, slot });
          continue;
        }
        next.push(existing);
      }

      for (const existing of current) {
        if (activeIds.has(existing.taskId)) continue;
        if (existing.phase === "walking-to-exit" || existing.phase === "at-exit") {
          next.push(existing);
          continue;
        }
        next.push({ ...existing, phase: "walking-to-exit", phaseChangedAt: now });
      }

      return next.sort((a, b) => a.slot - b.slot);
    });
  }, [activeTasks, claimSlotForTask]);

  // -- Scene worker phase timer ---------------------------------------------
  useEffect(() => {
    if (sceneWorkers.length === 0) return;

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
            next.push({ ...worker, phase: nextPhase, phaseChangedAt: now });
            hasChanges = true;
            continue;
          }
          next.push(worker);
        }

        return hasChanges ? next : current;
      });
    }, 100);

    return () => window.clearInterval(handle);
  }, [sceneWorkers.length]);

  // -- Service health polling -----------------------------------------------
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      const result = await fetchServiceHealth();
      if (!cancelled) setServiceHealthState(result);
    };
    void check();
    const handle = window.setInterval(() => void check(), 15_000);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  // -- Claude Code usage polling (hourly) -----------------------------------
  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      const data = await fetchClaudeUsage();
      if (!cancelled) setClaudeUsage(data);
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

  // -- Load schedules on view switch ----------------------------------------
  useEffect(() => {
    if (mainView === "schedules") void loadSchedules();
  }, [mainView, loadSchedules]);

  // -- Server config (native auth default) ----------------------------------
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const hasExplicitNativeAuth = params.get("use_native_cli_auth") !== null;
    if (hasExplicitNativeAuth) return;
    fetchServerConfig().then((config) => {
      if (config) {
        setForm((current) => ({
          ...current,
          use_native_cli_auth: config.native_auth_default,
        }));
      }
    }).catch(() => { /* server config fetch is best-effort */ });
  }, [setForm]);

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
          chatOnCooldown={chatOnCooldown}
          onTriggerEmote={triggerEmote}
          playerNameInput={playerNameInput}
          onPlayerNameChange={setPlayerNameInput}
          playerColorInput={playerColorInput}
          onPlayerColorChange={setPlayerColorInput}
          claudeUsage={claudeUsage}
          claudeUsageLoading={claudeUsageLoading}
          onRefreshClaudeUsage={() => void refreshClaudeUsage()}
          floatingNumbers={floatingNumbers}
          decorations={decorations}
          onPlaceDecoration={placeDecoration}
          onClearDecorations={clearDecorations}
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
