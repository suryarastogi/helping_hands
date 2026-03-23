/**
 * HandWorldScene — the full zen-garden / factory scene for Hand World.
 *
 * Renders the background decorations, factory entrance, incinerator exit,
 * work desks, player avatars (local + remote), worker sprites, and the
 * two HUD panels (status summary + Claude usage).
 */
import { type CSSProperties, type Ref, useEffect, useRef, useState } from "react";

import { CHAT_MAX_LENGTH } from "../constants";

import type { RemotePlayer } from "../hooks/useMultiplayer";
import type { ConnectionStatus } from "../hooks/useMultiplayer";
import { savePlayerName } from "../hooks/useMultiplayer";
import type {
  CharacterStyle,
  ChatMessage,
  ClaudeUsageResponse,
  DeskSlot,
  FloatingNumber,
  PlayerDirection,
  PlayerPosition,
  SceneWorkerPhase,
  ScheduleItem,
  WorkerVariant,
} from "../types";
import PlayerAvatar from "./PlayerAvatar";
import WorkerSprite from "./WorkerSprite";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Enriched worker entry with task/desk/style data, as computed in App.tsx. */
export type SceneWorkerEntry = {
  taskId: string;
  slot: number;
  phase: SceneWorkerPhase;
  phaseChangedAt: number;
  task: {
    backend?: string;
    repoPath?: string;
    status?: string;
  } | null;
  desk: DeskSlot;
  isActive: boolean;
  provider: string;
  style: CharacterStyle;
  spriteVariant: WorkerVariant;
  schedule: ScheduleItem | null;
};

export type HandWorldSceneProps = {
  /** Ref forwarded onto the scene container div (used for focus/keyboard). */
  sceneRef: Ref<HTMLDivElement>;
  /** Inline style applied to the scene container (dynamic min-height). */
  sceneStyle: CSSProperties;
  /** Maximum desk/station count. */
  maxWorkers: number;
  /** Pre-computed desk slot positions. */
  deskSlots: DeskSlot[];
  /** Enriched scene worker entries (task + desk + style). */
  workerEntries: SceneWorkerEntry[];
  /** Currently selected task ID (highlights the worker). */
  selectedTaskId: string | null;
  /** Callback when a worker sprite is clicked. */
  onSelectTask: (taskId: string) => void;

  // -- Player state --
  playerDirection: PlayerDirection;
  isPlayerWalking: boolean;
  playerPosition: PlayerPosition;
  localEmote: string | null;

  // -- Multiplayer state --
  remotePlayers: RemotePlayer[];
  remoteEmotes: Record<string, string>;
  remoteChats: Record<string, string>;
  localChat: string | null;
  isLocalIdle: boolean;
  connectionStatus: ConnectionStatus;
  chatHistory: ChatMessage[];
  onSendChat: (message: string) => void;

  // -- Player name --
  playerNameInput: string;
  onPlayerNameChange: (name: string) => void;

  // -- Claude usage --
  claudeUsage: ClaudeUsageResponse | null;
  claudeUsageLoading: boolean;
  onRefreshClaudeUsage: () => void;

  // -- Floating numbers --
  floatingNumbers: FloatingNumber[];
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function HandWorldScene({
  sceneRef,
  sceneStyle,
  maxWorkers,
  deskSlots,
  workerEntries,
  selectedTaskId,
  onSelectTask,
  playerDirection,
  isPlayerWalking,
  playerPosition,
  localEmote,
  remotePlayers,
  remoteEmotes,
  remoteChats,
  localChat,
  isLocalIdle,
  connectionStatus,
  chatHistory,
  onSendChat,
  playerNameInput,
  onPlayerNameChange,
  claudeUsage,
  claudeUsageLoading,
  onRefreshClaudeUsage,
  floatingNumbers,
}: HandWorldSceneProps) {
  const [chatInput, setChatInput] = useState("");
  const chatInputRef = useRef<HTMLInputElement>(null);
  const chatHistoryRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat history to bottom when new messages arrive.
  useEffect(() => {
    const el = chatHistoryRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [chatHistory.length]);

  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = chatInput.trim();
    if (!text) return;
    onSendChat(text);
    setChatInput("");
    chatInputRef.current?.blur();
  };

  return (
    <section className="card hand-world-card">
      <header className="header">
        <h1>Hand World</h1>
        <p>{maxWorkers} stations &middot; click a worker to stream its output</p>
      </header>

      <div
        ref={sceneRef}
        className="world-scene office-scene"
        role="list"
        aria-label="Current factory workers"
        style={sceneStyle}
        tabIndex={0}
      >
        <div className="zen-border" aria-hidden="true" />
        <div className="zen-sand-floor" aria-hidden="true" />

        {/* Sky & mountains backdrop */}
        <div className="zen-sky" aria-hidden="true">
          <div className="zen-mountain zen-mountain-1" />
          <div className="zen-mountain zen-mountain-2" />
          <div className="zen-mountain zen-mountain-3" />
          <div className="zen-moon" />
        </div>

        {/* Garden decorations */}
        <div className="zen-gravel-path" aria-hidden="true" />
        <div className="zen-bamboo" aria-hidden="true">
          <span className="bamboo-stalk bamboo-stalk-1" />
          <span className="bamboo-stalk bamboo-stalk-2" />
          <span className="bamboo-stalk bamboo-stalk-3" />
          <span className="bamboo-leaves" />
        </div>
        <div className="zen-maple" aria-hidden="true">
          <span className="maple-trunk" />
          <span className="maple-canopy maple-canopy-1" />
          <span className="maple-canopy maple-canopy-2" />
          <span className="maple-canopy maple-canopy-3" />
        </div>
        <div className="zen-lantern" aria-hidden="true">
          <span className="lantern-cap" />
          <span className="lantern-light" />
          <span className="lantern-base" />
          <span className="lantern-glow" />
        </div>
        <div className="zen-rock zen-rock-lg" aria-hidden="true" />
        <div className="zen-rock zen-rock-sm" aria-hidden="true" />

        {/* Factory entrance (middle-left) */}
        <div className="hh-factory" aria-hidden="true">
          <span className="factory-building" />
          <span className="factory-roof" />
          <span className="factory-chimney" />
          <span className="factory-smoke factory-smoke-1" />
          <span className="factory-smoke factory-smoke-2" />
          <span className="factory-smoke factory-smoke-3" />
          <span className="factory-door" />
          <span className="factory-window factory-window-1" />
          <span className="factory-window factory-window-2" />
          <span className="factory-conveyor" />
          <span className="factory-conveyor-line factory-conveyor-line-1" />
          <span className="factory-conveyor-line factory-conveyor-line-2" />
          <span className="factory-conveyor-line factory-conveyor-line-3" />
          <span className="factory-light" />
          <div className="factory-label">FACTORY</div>
        </div>

        {/* Incinerator exit (middle-right) */}
        <div className="hh-incinerator" aria-hidden="true">
          <span className="incinerator-body" />
          <span className="incinerator-top" />
          <span className="incinerator-mouth" />
          <span className="incinerator-grate" />
          <span className="incinerator-flame incinerator-flame-1" />
          <span className="incinerator-flame incinerator-flame-2" />
          <span className="incinerator-flame incinerator-flame-3" />
          <span className="incinerator-ember incinerator-ember-1" />
          <span className="incinerator-ember incinerator-ember-2" />
          <span className="incinerator-heat-glow" />
          <span className="incinerator-chimney" />
          <span className="incinerator-exhaust incinerator-exhaust-1" />
          <span className="incinerator-exhaust incinerator-exhaust-2" />
          <div className="incinerator-label">INCINERATOR</div>
        </div>

        {deskSlots.map((slot, slotIdx) => {
          const occupant = workerEntries.find((w) => w.slot === slotIdx);
          const showMonitor = occupant && (occupant.phase === "walking-to-desk" || occupant.phase === "active");
          return (
            <div
              key={slot.id}
              className="work-desk"
              style={{ left: `${slot.left}%`, top: `${slot.top}%` }}
              aria-hidden="true"
            >
              {showMonitor && (
                <span className={`desk-monitor${occupant.phase === "active" ? " monitor-on" : ""}`}>
                  <span className="monitor-screen" />
                  <span className="monitor-stand" />
                  <span className="monitor-base" />
                  <span className="monitor-glow" />
                </span>
              )}
            </div>
          );
        })}

        <div className="zen-status-summary">
          <div className="status-summary-header">Factory Floor</div>
          <div className="status-summary-stat">
            <span className="stat-icon">&#128187;</span>
            <span>{maxWorkers} Stations</span>
          </div>
          <div className="status-summary-stat">
            <span className="stat-icon">&#129302;</span>
            <span>{workerEntries.length} Active</span>
          </div>
          <div className="status-summary-stat player-name-row">
            <span className="stat-icon">&#128100;</span>
            <input
              type="text"
              className="player-name-input"
              value={playerNameInput}
              onChange={(e) => {
                onPlayerNameChange(e.target.value);
                savePlayerName(e.target.value);
              }}
              placeholder="Your name"
              maxLength={24}
              aria-label="Player name"
            />
          </div>
          {remotePlayers.length > 0 && (
            <div className="presence-panel" aria-label="Connected players">
              <div className="presence-header">
                <span className="stat-icon">&#128101;</span>
                <span>{remotePlayers.length + 1} Online</span>
              </div>
              <ul className="presence-list">
                {remotePlayers.map((rp) => (
                  <li key={rp.player_id} className="presence-item">
                    <span
                      className="presence-dot"
                      style={{ backgroundColor: rp.color }}
                    />
                    <span className="presence-name">
                      {rp.name}{rp.idle ? " (idle)" : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="status-summary-hint">
            <span className={`conn-status-dot conn-status-${connectionStatus}`} aria-label={`Connection: ${connectionStatus}`} />
            {connectionStatus === "connected"
              ? "Multiplayer active \u00b7 Arrow keys: walk \u00b7 1-4: emote"
              : connectionStatus === "connecting"
                ? "Connecting\u2026"
                : "Disconnected \u00b7 Arrow keys: walk"}
          </div>
          {connectionStatus === "connected" && (
            <form className="chat-input-form" onSubmit={handleChatSubmit}>
              <input
                ref={chatInputRef}
                type="text"
                className="chat-input"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Press Enter to chat..."
                maxLength={CHAT_MAX_LENGTH}
                aria-label="Chat message"
              />
            </form>
          )}
          {chatHistory.length > 0 && (
            <div
              ref={chatHistoryRef}
              className="chat-history-panel"
              aria-label="Chat history"
            >
              {chatHistory.map((msg) => (
                <div key={msg.id} className="chat-history-message">
                  <span
                    className="chat-history-name"
                    style={{ color: msg.playerColor }}
                  >
                    {msg.playerName}
                  </span>
                  <span className="chat-history-text">{msg.text}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="zen-usage-summary">
          <div className="status-summary-header">
            Claude Usage
            <button
              type="button"
              className="usage-refresh-btn"
              onClick={onRefreshClaudeUsage}
              disabled={claudeUsageLoading}
              title="Refresh usage"
            >
              &#8635;
            </button>
          </div>
          {claudeUsageLoading && !claudeUsage && (
            <div className="usage-meter-row">
              <span className="usage-placeholder">Loading...</span>
            </div>
          )}
          {claudeUsage?.error && (
            <div className="usage-error">{claudeUsage.error}</div>
          )}
          {claudeUsage && !claudeUsage.error && claudeUsage.levels.map((level) => (
            <div key={level.name} className="usage-meter-row">
              <span className="usage-meter-label">{level.name}</span>
              <div className="usage-meter-track">
                <div
                  className={`usage-meter-fill${level.percent_used >= 90 ? " crit" : level.percent_used >= 70 ? " warn" : ""}`}
                  style={{ width: `${Math.min(level.percent_used, 100)}%` }}
                />
              </div>
              <span className="usage-meter-pct">{Math.round(level.percent_used)}%</span>
            </div>
          ))}
          {!claudeUsage && !claudeUsageLoading && (
            <div className="usage-meter-row">
              <span className="usage-placeholder">Click &#8635; to load</span>
            </div>
          )}
        </div>

        <PlayerAvatar
          direction={playerDirection}
          walking={isPlayerWalking}
          emote={localEmote}
          chat={localChat}
          idle={isLocalIdle}
          isLocal
          x={playerPosition.x}
          y={playerPosition.y}
        />

        {remotePlayers.map((rp) => (
          <PlayerAvatar
            key={rp.player_id}
            direction={rp.direction}
            walking={rp.walking}
            name={rp.name}
            emote={remoteEmotes[rp.player_id]}
            chat={remoteChats[rp.player_id]}
            idle={rp.idle}
            color={rp.color}
            x={rp.x}
            y={rp.y}
          />
        ))}

        {workerEntries.map((worker) => (
          <WorkerSprite
            key={worker.taskId}
            taskId={worker.taskId}
            phase={worker.phase}
            style={worker.style}
            spriteVariant={worker.spriteVariant}
            isActive={worker.isActive}
            isSelected={selectedTaskId === worker.taskId}
            provider={worker.provider}
            deskLeft={worker.desk.left}
            deskTop={worker.desk.top}
            task={{
              backend: worker.task?.backend,
              repoPath: worker.task?.repoPath,
              status: worker.task?.status,
            }}
            schedule={worker.schedule}
            floatingNumbers={floatingNumbers.filter(
              (f) => f.taskId === worker.taskId,
            )}
            onSelect={onSelectTask}
          />
        ))}
      </div>
    </section>
  );
}
