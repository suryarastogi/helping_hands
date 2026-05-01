import { useEffect, useMemo, useRef, useState } from "react";

/** Per-tab stable id for multiplayer grill participation (vote dedup, chat
 *  attribution). Survives refresh but not new-tab — matches the per-tab
 *  voting semantics locked in the FINAL PLAN. */
function loadOrCreateMGrillPlayerId(): string {
  try {
    const key = "hh_mgrill_player_id_v1";
    const existing = sessionStorage.getItem(key);
    if (existing) return existing;
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2);
    sessionStorage.setItem(key, id);
    return id;
  } catch {
    return Math.random().toString(36).slice(2);
  }
}

import AppOverlays from "./components/AppOverlays";
import AsteroidsGame from "./components/AsteroidsGame";
import GrillMeOverlay from "./components/GrillMeOverlay";
import MultiplayerGrillOverlay from "./components/MultiplayerGrillOverlay";
import OnboardingOverlay from "./components/OnboardingOverlay";
import ChatPanel from "./components/ChatPanel";
import HandWorldScene from "./components/HandWorldScene";
import MonitorCard from "./components/MonitorCard";
import ScheduleCard from "./components/ScheduleCard";
import SubmissionForm from "./components/SubmissionForm";
import SubmitIssueOverlay from "./components/SubmitIssueOverlay";
import TaskListSidebar from "./components/TaskListSidebar";
import { useClaudeUsage } from "./hooks/useClaudeUsage";
import { useGrillSession } from "./hooks/useGrillSession";
import { useOnboarding } from "./hooks/useOnboarding";
import { useMovement } from "./hooks/useMovement";
import { useMultiplayer, loadPlayerName, loadPlayerColor } from "./hooks/useMultiplayer";
import { useRecentRepos } from "./hooks/useRecentRepos";
import { useSceneWorkers } from "./hooks/useSceneWorkers";
import { useSchedules } from "./hooks/useSchedules";
import { useServiceHealth } from "./hooks/useServiceHealth";
import { useTaskManager } from "./hooks/useTaskManager";
import type { Backend } from "./types";
import {
  apiUrl,
  asRecord,
  BACKEND_OPTIONS,
  defaultModelForBackend,
  fetchServerConfig,
  filterEnabledBackends,
  isTerminalTaskStatus,
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
    linkedIssueNumber,
    runtimeDisplay,
    monitorOutputRef,
    monitorHeight,
    handleMonitorScroll,
    handleResizeStart,
    floatingNumbers,
    toasts,
    removeToast,
    fetchedCapacity,
    lastOutputByTaskId,
    submitRun,
    submitBuild,
    selectTask,
    openSubmissionView,
  } = useTaskManager();

  // -- Diff & file tree polling for the current task ------------------------
  const [diffFiles, setDiffFiles] = useState<{ filename: string; status: string; diff: string }[]>([]);
  const [diffError, setDiffError] = useState<string | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffIsCommitted, setDiffIsCommitted] = useState(false);
  const diffSnapshotsRef = useRef<Map<string, { filename: string; status: string; diff: string }[]>>(new Map());
  const [fileTree, setFileTree] = useState<{ path: string; name: string; type: "file" | "dir"; status: string | null }[]>([]);
  const [fileTreeError, setFileTreeError] = useState<string | null>(null);
  const [fileTreeLoading, setFileTreeLoading] = useState(false);
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
  } = useSchedules(form.github_token);
  const { recentRepos } = useRecentRepos();
  const [serverHasGithubToken, setServerHasGithubToken] = useState(true);
  const onboarding = useOnboarding({
    hasActiveTasks: activeTaskIds.size > 0,
    hasSchedules: schedules.length > 0,
    serverHasGithubToken,
  });

  const [enabledBackends, setEnabledBackends] = useState<Backend[]>(BACKEND_OPTIONS);
  const [showClaudeUsage, setShowClaudeUsage] = useState(true);
  const [grillEnabled, setGrillEnabled] = useState(false);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [arcadeOpen, setArcadeOpen] = useState(false);
  const [playerNameInput, setPlayerNameInput] = useState(loadPlayerName);
  const [playerColorInput, setPlayerColorInput] = useState(loadPlayerColor);
  const [showGrillOverlay, setShowGrillOverlay] = useState(false);
  const [showMGrillOverlay, setShowMGrillOverlay] = useState(false);
  const [showSubmitIssueOverlay, setShowSubmitIssueOverlay] = useState(false);
  const [mgrillPlayerId] = useState(loadOrCreateMGrillPlayerId);
  const grillSession = useGrillSession();

  const {
    maxOfficeWorkers,
    plotSlots,
    sceneWorkerEntries,
    worldSceneStyle,
  } = useSceneWorkers({
    activeTasks,
    activeTaskIds,
    taskById,
    fetchedCapacity,
    schedules,
    lastOutputByTaskId,
  });

  const {
    playerPosition,
    playerDirection,
    isPlayerWalking,
  } = useMovement({ active: !arcadeOpen, plotSlots });

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
    decoOnCooldown,
    decorations,
    placeDecoration,
    clearDecorations,
    remoteCursors,
    updateCursor,
    localPlayerName,
  } = useMultiplayer({
    active: true,
    playerPosition,
    playerDirection,
    isPlayerWalking,
    wsUrlBuilder: wsUrl,
    playerName: playerNameInput,
    playerColor: playerColorInput,
  });

  // -- Onboarding: auto-open submission overlay for form-targeting steps -----
  useEffect(() => {
    if (!onboarding.isActive || !onboarding.currentStep) return;
    const formStepIds = ["repo-input", "prompt-input", "github-token", "submit-btn"];
    if (formStepIds.includes(onboarding.currentStep.id) && !showSubmissionOverlay) {
      setShowSubmissionOverlay(true);
    }
    // Auto-open the Advanced <details> when the github-token step is active
    if (onboarding.currentStep.id === "github-token") {
      requestAnimationFrame(() => {
        const details = document.querySelector<HTMLDetailsElement>(".submission-overlay .compact-advanced");
        if (details && !details.open) {
          details.open = true;
        }
      });
    }
  }, [onboarding.isActive, onboarding.currentStep, showSubmissionOverlay, setShowSubmissionOverlay]);

  // -- Load schedules on view switch ----------------------------------------
  useEffect(() => {
    if (mainView === "schedules") void loadSchedules();
  }, [mainView, loadSchedules]);

  // -- Poll diff for the currently selected task ----------------------------
  useEffect(() => {
    if (!taskId) {
      setDiffFiles([]);
      setDiffError(null);
      setDiffIsCommitted(false);
      return;
    }

    // On task switch, restore snapshot if one exists
    const existingSnapshot = diffSnapshotsRef.current.get(taskId);
    if (existingSnapshot) {
      setDiffFiles(existingSnapshot);
      setDiffIsCommitted(true);
    }

    let cancelled = false;

    const fetchDiff = async () => {
      setDiffLoading(true);
      try {
        const res = await fetch(apiUrl(`/tasks/${taskId}/diff?_=${Date.now()}`), {
          cache: "no-store",
        });
        if (!res.ok || cancelled) return;
        const data = await res.json();
        if (cancelled) return;
        const files = data.files ?? [];
        if (files.length > 0) {
          setDiffFiles(files);
          diffSnapshotsRef.current.set(taskId, files);
          setDiffIsCommitted(false);
        } else {
          const snapshot = diffSnapshotsRef.current.get(taskId);
          if (snapshot) {
            setDiffFiles(snapshot);
            setDiffIsCommitted(true);
          } else {
            setDiffFiles([]);
            setDiffIsCommitted(false);
          }
        }
        setDiffError(data.error ?? null);
      } catch {
        if (!cancelled) {
          setDiffError("Failed to fetch diff");
        }
      } finally {
        if (!cancelled) setDiffLoading(false);
      }
    };

    void fetchDiff();
    const isActive = !isTerminalTaskStatus(status);
    if (isActive) {
      const handle = window.setInterval(() => void fetchDiff(), 5000);
      return () => { cancelled = true; window.clearInterval(handle); };
    }
    return () => { cancelled = true; };
  }, [taskId, status]);

  // -- Fetch file tree for the currently selected task ----------------------
  useEffect(() => {
    if (!taskId) {
      setFileTree([]);
      setFileTreeError(null);
      return;
    }
    let cancelled = false;

    const fetchTree = async () => {
      setFileTreeLoading(true);
      try {
        const res = await fetch(apiUrl(`/tasks/${taskId}/tree?_=${Date.now()}`), {
          cache: "no-store",
        });
        if (!res.ok || cancelled) return;
        const data = await res.json();
        if (cancelled) return;
        setFileTree(data.tree ?? []);
        setFileTreeError(data.error ?? null);
      } catch {
        if (!cancelled) setFileTreeError("Failed to fetch file tree");
      } finally {
        if (!cancelled) setFileTreeLoading(false);
      }
    };

    void fetchTree();
    const isActive = !isTerminalTaskStatus(status);
    if (isActive) {
      const handle = window.setInterval(() => void fetchTree(), 10000);
      return () => { cancelled = true; window.clearInterval(handle); };
    }
    return () => { cancelled = true; };
  }, [taskId, status]);

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
              return {
                ...current,
                backend: filtered[0],
                model: defaultModelForBackend(filtered[0]),
              };
            }
            return current;
          });
        }
        if (config.claude_native_cli_auth === false) {
          setShowClaudeUsage(false);
        }
        if (config.has_github_token === false) {
          setServerHasGithubToken(false);
        }
        if (config.default_repo) {
          setForm((current) => ({
            ...current,
            repo_path: config.default_repo!,
          }));
        }
        if (config.grill_enabled) {
          setGrillEnabled(true);
        }
      }
    }).catch(() => { /* server config fetch is best-effort */ });
  }, [setForm]);

  // Keep schedule form backend in sync with enabled backends.
  useEffect(() => {
    if (enabledBackends.length > 0 && !enabledBackends.includes(scheduleForm.backend)) {
      updateScheduleField("backend", enabledBackends[0]);
    }
  }, [enabledBackends, scheduleForm.backend, updateScheduleField]);

  const taskError = useMemo<{ error: string; errorType: string } | null>(() => {
    if (statusTone(status) !== "fail") return null;
    const result = asRecord((payload as Record<string, unknown> | null)?.result);
    const error = typeof result?.error === "string" ? result.error : null;
    const errorType = typeof result?.error_type === "string" ? result.error_type : null;
    if (!error) return null;
    return { error, errorType: errorType ?? "Error" };
  }, [status, payload]);

  const handleOpenGrill = () => {
    grillSession.reset();
    setShowGrillOverlay(true);
  };

  const handleGrillSubmitPlan = (plan: string) => {
    setShowGrillOverlay(false);
    grillSession.reset();

    // Submit directly with the plan and grill form fields, bypassing
    // form state timing issues.
    void submitBuild({
      prompt: plan,
      repo_path: grillInitialForm.repo_path || form.repo_path,
      github_token: grillInitialForm.github_token || form.github_token,
      reference_repos: grillInitialForm.reference_repos || form.reference_repos,
    });
  };

  const handleSubmitIssue = (repo: string, issue: { number: number; title: string; body: string }, githubToken: string) => {
    setShowSubmitIssueOverlay(false);
    const prompt = issue.body
      ? `${issue.title}\n\n${issue.body}`
      : issue.title;
    setForm((current) => ({
      ...current,
      repo_path: repo,
      prompt,
      issue_number: String(issue.number),
      ...(githubToken.trim() ? { github_token: githubToken.trim() } : {}),
    }));
    setShowSubmissionOverlay(true);
  };

  const grillInitialForm = useMemo(() => ({
    repo_path: form.repo_path,
    prompt: form.prompt,
    model: form.model,
    github_token: form.github_token,
    reference_repos: form.reference_repos,
    backend: form.backend,
  }), [form.repo_path, form.prompt, form.model, form.github_token, form.reference_repos, form.backend]);

  const submissionCard = (
    <SubmissionForm form={form} onFieldChange={updateField} onSubmit={submitRun} backends={enabledBackends} recentRepos={recentRepos} serverHasGithubToken={serverHasGithubToken} />
  );

  const monitorCard = (
    <MonitorCard
      taskId={taskId}
      issueNumber={linkedIssueNumber}
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
      diffFiles={diffFiles}
      diffError={diffError}
      diffLoading={diffLoading}
      fileTree={fileTree}
      fileTreeError={fileTreeError}
      fileTreeLoading={fileTreeLoading}
      diffIsCommitted={diffIsCommitted}
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
      serverHasGithubToken={serverHasGithubToken}
    />
  );

  return (
    <>
    <main className={`page${leftCollapsed ? " left-collapsed" : ""}${rightCollapsed ? " right-collapsed" : ""}`}>
      <TaskListSidebar
        mainView={mainView}
        showSubmissionOverlay={showSubmissionOverlay}
        onNewSubmission={openSubmissionView}
        onGrillMe={grillEnabled ? handleOpenGrill : undefined}
        onSubmitIssue={() => setShowSubmitIssueOverlay(true)}
        onToggleSchedules={() => setMainView(v => v === "schedules" ? "submission" : "schedules")}
        onStartTutorial={onboarding.restart}
        taskHistory={taskHistory}
        selectedTaskId={taskId}
        onSelectTask={selectTask}
        onClearHistory={() => setTaskHistory([])}
        collapsed={leftCollapsed}
        onToggleCollapsed={() => setLeftCollapsed(v => !v)}
      />

      <div className="main-column">
        {arcadeOpen && (
          <AsteroidsGame onClose={() => setArcadeOpen(false)} playerName={localPlayerName} />
        )}

        <HandWorldScene
          sceneRef={sceneRef}
          sceneStyle={worldSceneStyle}
          maxWorkers={maxOfficeWorkers}
          plotSlots={plotSlots}
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
          claudeUsage={claudeUsage}
          claudeUsageLoading={claudeUsageLoading}
          onRefreshClaudeUsage={() => void refreshClaudeUsage()}
          showClaudeUsage={showClaudeUsage}
          floatingNumbers={floatingNumbers}
          decorations={decorations}
          onPlaceDecoration={placeDecoration}
          onClearDecorations={clearDecorations}
          decoOnCooldown={decoOnCooldown}
          remoteCursors={remoteCursors}
          onCursorMove={updateCursor}
          arcadeOpen={arcadeOpen}
          onArcadeOpen={() => setArcadeOpen(true)}
          mgrillOpen={showMGrillOverlay}
          onMGrillOpen={() => setShowMGrillOverlay(true)}
          mgrillEnabled={grillEnabled}
        />

        {mainView === "monitor" && taskId && monitorCard}
        {mainView === "schedules" && schedulesCard}
      </div>

      <ChatPanel
        remotePlayers={remotePlayers}
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
        collapsed={rightCollapsed}
        onToggleCollapsed={() => setRightCollapsed(v => !v)}
      />

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
    {grillEnabled && showGrillOverlay && (
      <GrillMeOverlay
        session={grillSession}
        recentRepos={recentRepos}
        serverHasGithubToken={serverHasGithubToken}
        initialForm={grillInitialForm}
        onClose={() => {
          setShowGrillOverlay(false);
          grillSession.reset();
        }}
        onSubmitPlan={handleGrillSubmitPlan}
      />
    )}
    {grillEnabled && showMGrillOverlay && (
      <MultiplayerGrillOverlay
        onClose={() => setShowMGrillOverlay(false)}
        onSubmitPlan={(taskId) => {
          // Surface the submitted task in the existing task list by
          // selecting it — matches the solo-grill plan-submit hand-off.
          selectTask(taskId);
          setShowMGrillOverlay(false);
        }}
        playerId={mgrillPlayerId}
        playerName={localPlayerName}
        initialCreateForm={{
          repo_path: form.repo_path,
          prompt: form.prompt,
          model: form.model,
          backend: form.backend,
          reference_repos: form.reference_repos,
        }}
        serverHasGithubToken={serverHasGithubToken}
      />
    )}
    {showSubmitIssueOverlay && (
      <SubmitIssueOverlay
        recentRepos={recentRepos}
        serverHasGithubToken={serverHasGithubToken}
        defaultRepo={form.repo_path}
        onSubmitIssue={handleSubmitIssue}
        onClose={() => setShowSubmitIssueOverlay(false)}
      />
    )}
    <AppOverlays
      serviceHealthState={serviceHealthState}
      toasts={toasts}
      onRemoveToast={removeToast}
    />
    {onboarding.isActive && onboarding.currentStep && (
      <OnboardingOverlay
        step={onboarding.currentStep}
        stepIndex={onboarding.currentStepIndex!}
        totalSteps={onboarding.totalSteps}
        onNext={onboarding.nextStep}
        onPrev={onboarding.prevStep}
        onDismiss={onboarding.dismiss}
      />
    )}
    </>
  );
}
