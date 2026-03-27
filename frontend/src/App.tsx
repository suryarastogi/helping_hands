import { useEffect, useMemo, useRef, useState } from "react";

import AppOverlays from "./components/AppOverlays";
import HandWorldScene from "./components/HandWorldScene";
import MonitorCard from "./components/MonitorCard";
import ScheduleCard from "./components/ScheduleCard";
import SubmissionForm from "./components/SubmissionForm";
import TaskListSidebar from "./components/TaskListSidebar";
import { useClaudeUsage } from "./hooks/useClaudeUsage";
import { useMovement } from "./hooks/useMovement";
import { useMultiplayer, loadPlayerName, loadPlayerColor } from "./hooks/useMultiplayer";
import { useRecentRepos } from "./hooks/useRecentRepos";
import { useSceneWorkers } from "./hooks/useSceneWorkers";
import { useSchedules } from "./hooks/useSchedules";
import { useServiceHealth } from "./hooks/useServiceHealth";
import { useTaskManager } from "./hooks/useTaskManager";
import type { Backend } from "./types";
import {
  asRecord,
  BACKEND_OPTIONS,
  fetchServerConfig,
  filterEnabledBackends,
  statusTone,
  wsUrl,
} from "./App.utils";

export default function App() {
  const {
    form,
    updateField,
    setForm,
    taskId,
    status,
    payload,
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

  const sceneRef = useRef<HTMLDivElement>(null);
  const serviceHealthState = useServiceHealth();
  const { claudeUsage, claudeUsageLoading, refreshClaudeUsage } = useClaudeUsage();
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
  const { recentRepos } = useRecentRepos();
  const [enabledBackends, setEnabledBackends] = useState<Backend[]>(BACKEND_OPTIONS);
  const [showClaudeUsage, setShowClaudeUsage] = useState(true);
  const [playerNameInput, setPlayerNameInput] = useState(loadPlayerName);
  const [playerColorInput, setPlayerColorInput] = useState(loadPlayerColor);

  const {
    maxOfficeWorkers,
    deskSlots,
    sceneWorkerEntries,
    worldSceneStyle,
  } = useSceneWorkers({
    activeTasks,
    activeTaskIds,
    taskById,
    fetchedCapacity,
    schedules,
  });

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
    remoteCursors,
    updateCursor,
  } = useMultiplayer({
    active: true,
    playerPosition,
    playerDirection,
    isPlayerWalking,
    wsUrlBuilder: wsUrl,
    playerName: playerNameInput,
    playerColor: playerColorInput,
  });

  // -- Load schedules on view switch ----------------------------------------
  useEffect(() => {
    if (mainView === "schedules") void loadSchedules();
  }, [mainView, loadSchedules]);

  // -- Server config (native auth default, enabled backends) ----------------
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
        const filtered = filterEnabledBackends(BACKEND_OPTIONS, config.enabled_backends);
        if (filtered.length > 0) {
          setEnabledBackends(filtered);
          setForm((current) => {
            if (!filtered.includes(current.backend)) {
              return { ...current, backend: filtered[0] };
            }
            return current;
          });
        }
        if (config.claude_native_cli_auth === false) {
          setShowClaudeUsage(false);
        }
      }
    }).catch(() => { /* server config fetch is best-effort */ });
  }, [setForm]);

  const taskError = useMemo<{ error: string; errorType: string } | null>(() => {
    if (statusTone(status) !== "fail") return null;
    const result = asRecord((payload as Record<string, unknown> | null)?.result);
    const error = typeof result?.error === "string" ? result.error : null;
    const errorType = typeof result?.error_type === "string" ? result.error_type : null;
    if (!error) return null;
    return { error, errorType: errorType ?? "Error" };
  }, [status, payload]);

  const submissionCard = (
    <SubmissionForm form={form} onFieldChange={updateField} onSubmit={submitRun} backends={enabledBackends} recentRepos={recentRepos} />
  );

  const monitorCard = (
    <MonitorCard
      taskId={taskId}
      status={status}
      taskError={taskError}
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
      backends={enabledBackends}
      onUpdateField={updateScheduleField}
      onNewSchedule={openNewScheduleForm}
      onEditSchedule={openEditScheduleForm}
      onSaveSchedule={saveSchedule}
      onDeleteSchedule={deleteSchedule}
      onTriggerSchedule={triggerSchedule}
      onToggleSchedule={toggleSchedule}
      onCancelForm={cancelScheduleForm}
      onRefresh={loadSchedules}
      recentRepos={recentRepos}
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
          showClaudeUsage={showClaudeUsage}
          floatingNumbers={floatingNumbers}
          decorations={decorations}
          onPlaceDecoration={placeDecoration}
          onClearDecorations={clearDecorations}
          remoteCursors={remoteCursors}
          onCursorMove={updateCursor}
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
              &times;
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
