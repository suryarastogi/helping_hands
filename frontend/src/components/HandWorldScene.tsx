/**
 * HandWorldScene — the full zen-garden / factory scene for Hand World.
 *
 * Renders the background decorations, factory entrance, incinerator exit,
 * work desks, player avatars (local + remote), worker sprites, and the
 * two HUD panels (status summary + Claude usage).
 */
import { type CSSProperties, type Ref, useEffect, useRef, useState } from "react";

import { CHAT_MAX_LENGTH, DECORATION_EMOJIS, EMOTE_KEY_BINDINGS, EMOTE_MAP, MAX_DECORATIONS, PLAYER_COLORS } from "../constants";

import type { RemotePlayer } from "../hooks/useMultiplayer";
import type { ConnectionStatus } from "../hooks/useMultiplayer";
import { savePlayerColor, savePlayerName } from "../hooks/useMultiplayer";
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
  WorldDecoration,
  WorkerVariant,
} from "../types";
import Minimap from "./Minimap";
import type { MinimapWorker } from "./Minimap";
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
  remoteTyping: Record<string, boolean>;
  localChat: string | null;
  isLocalIdle: boolean;
  isLocalTyping: boolean;
  connectionStatus: ConnectionStatus;
  chatHistory: ChatMessage[];
  onSendChat: (message: string) => void;
  onSetTyping: (typing: boolean) => void;
  /** Whether chat is on cooldown (disables send). */
  chatOnCooldown: boolean;
  /** Trigger an emote by key ("1"–"4"). */
  onTriggerEmote: (key: string) => void;

  // -- Player name & color --
  playerNameInput: string;
  onPlayerNameChange: (name: string) => void;
  playerColorInput: string;
  onPlayerColorChange: (color: string) => void;

  // -- Claude usage --
  claudeUsage: ClaudeUsageResponse | null;
  claudeUsageLoading: boolean;
  onRefreshClaudeUsage: () => void;

  // -- Floating numbers --
  floatingNumbers: FloatingNumber[];

  // -- Shared decorations --
  decorations: WorldDecoration[];
  onPlaceDecoration: (emoji: string, x: number, y: number) => void;
  onClearDecorations: () => void;
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
  remoteTyping,
  localChat,
  isLocalIdle,
  isLocalTyping,
  connectionStatus,
  chatHistory,
  onSendChat,
  onSetTyping,
  chatOnCooldown,
  onTriggerEmote,
  playerNameInput,
  onPlayerNameChange,
  playerColorInput,
  onPlayerColorChange,
  claudeUsage,
  claudeUsageLoading,
  onRefreshClaudeUsage,
  floatingNumbers,
  decorations,
  onPlaceDecoration,
  onClearDecorations,
}: HandWorldSceneProps) {
  const [chatInput, setChatInput] = useState("");
  const [emotePickerOpen, setEmotePickerOpen] = useState(false);
  const [selectedDecoEmoji, setSelectedDecoEmoji] = useState<string | null>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const chatHistoryRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat history to bottom when new messages arrive.
  useEffect(() => {
    const el = chatHistoryRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [chatHistory.length]);

  // Build minimap worker positions from desk slot centers.
  const minimapWorkers: MinimapWorker[] = workerEntries
    .filter((w) => w.phase === "active" || w.phase === "walking-to-desk")
    .map((w) => ({ taskId: w.taskId, x: w.desk.left + 4, y: w.desk.top + 3.5 }));

  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = chatInput.trim();
    if (!text || chatOnCooldown) return;
    onSendChat(text);
    setChatInput("");
    onSetTyping(false);
    chatInputRef.current?.blur();
  };

  const handleSceneDoubleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!selectedDecoEmoji || connectionStatus !== "connected") return;
    if (decorations.length >= MAX_DECORATIONS) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    onPlaceDecoration(selectedDecoEmoji, x, y);
    setSelectedDecoEmoji(null);
  };

  return (
    <section className="card hand-world-card">
      <header className="header">
        <h1>
          Hand World
          {connectionStatus === "connected" && (
            <span className="player-count-badge" aria-label={`${remotePlayers.length + 1} players online`}>
              {remotePlayers.length + 1}
            </span>
          )}
        </h1>
        <p>{maxWorkers} stations &middot; click a worker to stream its output</p>
      </header>

      <div
        ref={sceneRef}
        className={`world-scene office-scene${selectedDecoEmoji ? " deco-placing" : ""}`}
        role="list"
        aria-label="Current factory workers"
        style={sceneStyle}
        tabIndex={0}
        onDoubleClick={handleSceneDoubleClick}
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
          <div className="color-picker-row" aria-label="Player color">
            {PLAYER_COLORS.map((c) => (
              <button
                key={c}
                type="button"
                className={`color-swatch${playerColorInput === c ? " selected" : ""}`}
                style={{ backgroundColor: c }}
                onClick={() => {
                  onPlayerColorChange(c);
                  savePlayerColor(c);
                }}
                aria-label={`Select color ${c}`}
                aria-pressed={playerColorInput === c}
              />
            ))}
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
              ? "Multiplayer active \u00b7 Arrow keys: walk"
              : connectionStatus === "connecting"
                ? "Connecting\u2026"
                : "Disconnected \u00b7 Arrow keys: walk"}
            {connectionStatus === "connected" && (
              <button
                type="button"
                className="emote-picker-btn"
                onClick={() => setEmotePickerOpen((v) => !v)}
                aria-label="Toggle emote picker"
                aria-expanded={emotePickerOpen}
              >
                {emotePickerOpen ? "\u2716" : "\u{1F60A}"}
              </button>
            )}
          </div>
          {emotePickerOpen && connectionStatus === "connected" && (
            <div className="emote-picker-panel" role="group" aria-label="Emote picker">
              {Object.entries(EMOTE_KEY_BINDINGS).map(([key, emoteName]) => (
                <button
                  key={key}
                  type="button"
                  className="emote-picker-item"
                  onClick={() => {
                    onTriggerEmote(key);
                    setEmotePickerOpen(false);
                  }}
                  aria-label={`Send ${emoteName} emote`}
                >
                  <span className="emote-picker-emoji">{EMOTE_MAP[emoteName]}</span>
                  <span className="emote-picker-label">{emoteName}</span>
                  <kbd className="emote-picker-key">{key}</kbd>
                </button>
              ))}
            </div>
          )}
          {connectionStatus === "connected" && (
            <form className="chat-input-form" onSubmit={handleChatSubmit}>
              <input
                ref={chatInputRef}
                type="text"
                className="chat-input"
                value={chatInput}
                onChange={(e) => {
                  setChatInput(e.target.value);
                  onSetTyping(e.target.value.length > 0);
                }}
                onFocus={() => { if (chatInput.length > 0) onSetTyping(true); }}
                onBlur={() => onSetTyping(false)}
                placeholder={chatOnCooldown ? "Wait..." : "Press Enter to chat..."}
                maxLength={CHAT_MAX_LENGTH}
                disabled={chatOnCooldown}
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
                <div key={msg.id} className={`chat-history-message${msg.isSystem ? " chat-history-system" : ""}`}>
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
          {connectionStatus === "connected" && (
            <div className="decoration-toolbar" aria-label="Decoration toolbar">
              <div className="decoration-toolbar-header">
                <span>Decorations ({decorations.length}/{MAX_DECORATIONS})</span>
                {decorations.length > 0 && (
                  <button
                    type="button"
                    className="decoration-clear-btn"
                    onClick={onClearDecorations}
                    aria-label="Clear all decorations"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="decoration-palette" role="group" aria-label="Decoration emoji palette">
                {DECORATION_EMOJIS.map((emoji) => (
                  <button
                    key={emoji}
                    type="button"
                    className={`decoration-emoji-btn${selectedDecoEmoji === emoji ? " selected" : ""}`}
                    onClick={() => setSelectedDecoEmoji(selectedDecoEmoji === emoji ? null : emoji)}
                    disabled={decorations.length >= MAX_DECORATIONS}
                    aria-label={`Select ${emoji} decoration`}
                    aria-pressed={selectedDecoEmoji === emoji}
                  >
                    {emoji}
                  </button>
                ))}
              </div>
              {selectedDecoEmoji && (
                <div className="decoration-hint">Double-click the scene to place {selectedDecoEmoji}</div>
              )}
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
          typing={isLocalTyping}
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
            typing={remoteTyping[rp.player_id] ?? false}
            color={rp.color}
            x={rp.x}
            y={rp.y}
          />
        ))}

        {decorations.map((d) => (
          <span
            key={d.id}
            className="world-decoration"
            style={{ left: `${d.x}%`, top: `${d.y}%` }}
            title={`Placed by ${d.placedBy}`}
            aria-label={`${d.emoji} decoration by ${d.placedBy}`}
          >
            {d.emoji}
          </span>
        ))}

        {connectionStatus === "connected" && (
          <Minimap
            playerPosition={playerPosition}
            remotePlayers={remotePlayers}
            workers={minimapWorkers}
          />
        )}

        {connectionStatus === "connecting" && (
          <div className="reconnect-banner" role="alert" aria-label="Reconnecting">
            <span className="reconnect-spinner" />
            <span>Reconnecting&hellip;</span>
          </div>
        )}

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
