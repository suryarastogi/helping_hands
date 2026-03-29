/**
 * HandWorldScene — the full zen-garden / factory scene for Hand World.
 *
 * Renders the background decorations, factory entrance, incinerator exit,
 * work desks, player avatars (local + remote), worker sprites, and the
 * HUD overlay panels (FactoryFloorPanel + Claude usage).
 */
import { type CSSProperties, type Ref, useMemo, useState } from "react";

import { ARCADE_POSITION, ARCADE_PROXIMITY, MAX_DECORATIONS } from "../constants";

import type { RemoteCursor as RemoteCursorType } from "../hooks/useMultiplayer";
import type { RemotePlayer } from "../hooks/useMultiplayer";
import type { ConnectionStatus } from "../hooks/useMultiplayer";
import type { SceneWorkerEntry } from "../hooks/useSceneWorkers";
import type {
  ClaudeUsageResponse,
  CursorPosition,
  DeskSlot,
  FloatingNumber,
  PlayerDirection,
  PlayerPosition,
  WorldDecoration,
} from "../types";
import FactoryFloorPanel from "./FactoryFloorPanel";
import Minimap from "./Minimap";
import type { MinimapWorker } from "./Minimap";
import PlayerAvatar from "./PlayerAvatar";
import RemoteCursor from "./RemoteCursor";
import WorkerSprite from "./WorkerSprite";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type { SceneWorkerEntry } from "../hooks/useSceneWorkers";

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

  // -- Claude usage --
  claudeUsage: ClaudeUsageResponse | null;
  claudeUsageLoading: boolean;
  onRefreshClaudeUsage: () => void;
  showClaudeUsage?: boolean;

  // -- Floating numbers --
  floatingNumbers: FloatingNumber[];

  // -- Shared decorations --
  decorations: WorldDecoration[];
  onPlaceDecoration: (emoji: string, x: number, y: number) => void;
  onClearDecorations: () => void;
  /** Whether decoration placement is on cooldown. */
  decoOnCooldown: boolean;

  // -- Remote cursors --
  remoteCursors: RemoteCursorType[];
  onCursorMove: (position: CursorPosition | null) => void;

  // -- Arcade --
  /** Whether the arcade game is currently open. */
  arcadeOpen: boolean;
  /** Called when the player clicks the glowing card to open the arcade. */
  onArcadeOpen: () => void;
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
  claudeUsage,
  claudeUsageLoading,
  onRefreshClaudeUsage,
  showClaudeUsage = true,
  floatingNumbers,
  decorations,
  onPlaceDecoration,
  onClearDecorations,
  decoOnCooldown,
  remoteCursors,
  onCursorMove,
  arcadeOpen,
  onArcadeOpen,
}: HandWorldSceneProps) {
  const [selectedDecoEmoji, setSelectedDecoEmoji] = useState<string | null>(null);
  const [sidePanelOpen, setSidePanelOpen] = useState(false);

  // Proximity check: is the player near the arcade machine?
  const arcadeCenterX = ARCADE_POSITION.left + 4; // center of the sprite
  const arcadeCenterY = ARCADE_POSITION.top + 5;
  const nearArcade = useMemo(() => {
    const dx = playerPosition.x - arcadeCenterX;
    const dy = playerPosition.y - arcadeCenterY;
    return Math.sqrt(dx * dx + dy * dy) < ARCADE_PROXIMITY;
  }, [playerPosition.x, playerPosition.y, arcadeCenterX, arcadeCenterY]);

  // Build minimap worker positions from desk slot centers.
  const minimapWorkers: MinimapWorker[] = workerEntries
    .filter((w) => w.phase === "active" || w.phase === "walking-to-desk")
    .map((w) => ({ taskId: w.taskId, x: w.desk.left + 4, y: w.desk.top + 3.5 }));

  const handleSceneDoubleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!selectedDecoEmoji || connectionStatus !== "connected") return;
    if (decorations.length >= MAX_DECORATIONS || decoOnCooldown) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    onPlaceDecoration(selectedDecoEmoji, x, y);
    setSelectedDecoEmoji(null);
  };

  const handleSceneMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (connectionStatus !== "connected") return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    onCursorMove({ x, y });
  };

  const handleSceneMouseLeave = () => {
    onCursorMove(null);
  };

  return (
    <section
      className={`card hand-world-card${nearArcade && !arcadeOpen ? " arcade-glow" : ""}`}
      onClick={nearArcade && !arcadeOpen ? onArcadeOpen : undefined}
    >
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

      <div className="hand-world-layout">
      <div
        ref={sceneRef}
        className={`world-scene office-scene${selectedDecoEmoji ? " deco-placing" : ""}`}
        role="list"
        aria-label="Current factory workers"
        style={sceneStyle}
        tabIndex={0}
        onDoubleClick={handleSceneDoubleClick}
        onMouseMove={handleSceneMouseMove}
        onMouseLeave={handleSceneMouseLeave}
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

        {/* Arcade machine (top-right) */}
        <div className={`hh-arcade${nearArcade ? " arcade-active" : ""}`} aria-hidden="true">
          <span className="arcade-dust" />
          <span className="arcade-cabinet" />
          <span className="arcade-scratch arcade-scratch-1" />
          <span className="arcade-scratch arcade-scratch-2" />
          <span className="arcade-scratch arcade-scratch-3" />
          <span className="arcade-screen" />
          <span className="arcade-screen-crack" />
          <span className="arcade-screen-scanlines" />
          <span className="arcade-screen-glow" />
          <span className="arcade-controls" />
          <span className="arcade-base" />
          <span className="arcade-cobweb arcade-cobweb-tl" />
          <span className="arcade-cobweb arcade-cobweb-tr" />
          <span className="arcade-cobweb arcade-cobweb-br" />
          <div className="arcade-label">ARCADE</div>
          {nearArcade && !arcadeOpen && (
            <div className="arcade-prompt">Press to play!</div>
          )}
        </div>

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

        <button
          type="button"
          className="side-panel-toggle"
          onClick={() => setSidePanelOpen((v) => !v)}
          aria-label={sidePanelOpen ? "Hide side panel" : "Show side panel"}
          aria-expanded={sidePanelOpen}
          title={sidePanelOpen ? "Hide panel" : "Show panel"}
        >
          {sidePanelOpen ? "\u25B6" : "\u25C0"}
        </button>

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

        {remoteCursors.map((c) => (
          <RemoteCursor
            key={c.player_id}
            name={c.name}
            color={c.color}
            x={c.x}
            y={c.y}
          />
        ))}

        {connectionStatus === "connected" && (
          <Minimap
            playerPosition={playerPosition}
            remotePlayers={remotePlayers}
            workers={minimapWorkers}
          />
        )}

        {connectionStatus === "connecting" && (
          <div className="reconnect-banner" role="alert" aria-live="polite" aria-label="Reconnecting">
            <span className="reconnect-spinner" />
            <span>Reconnecting&hellip;</span>
          </div>
        )}

        {connectionStatus === "failed" && (
          <div className="reconnect-banner reconnect-failed" role="alert" aria-live="assertive" aria-label="Connection failed">
            <span>Connection failed after multiple attempts</span>
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

      <div className={`hand-world-side-panel${sidePanelOpen ? " open" : ""}`}>
        <FactoryFloorPanel
          maxWorkers={maxWorkers}
          activeWorkerCount={workerEntries.length}
          connectionStatus={connectionStatus}
          decorations={decorations}
          onClearDecorations={onClearDecorations}
          decoOnCooldown={decoOnCooldown}
          selectedDecoEmoji={selectedDecoEmoji}
          onSelectedDecoEmojiChange={setSelectedDecoEmoji}
        />

        {showClaudeUsage && (
        <div className="zen-usage-summary">
          <div className="status-summary-header">
            Claude Usage
            <button
              type="button"
              className="usage-refresh-btn"
              onClick={onRefreshClaudeUsage}
              disabled={claudeUsageLoading}
              title="Refresh usage"
              aria-label="Refresh Claude usage"
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
        )}
      </div>
      </div>
    </section>
  );
}
