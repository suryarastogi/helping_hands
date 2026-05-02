/**
 * HandWorldScene — the full zen-garden scene for Hand World.
 *
 * Renders the background decorations, torii gate entrance, garden plots,
 * player avatars (local + remote), worker sprites, and the HUD overlay
 * panels (GardenPanel + Claude usage).
 */
import { type CSSProperties, type Ref, useMemo, useState } from "react";

import {
  ARCADE_POSITION,
  ARCADE_PROXIMITY,
  MAX_DECORATIONS,
  MGRILL_POSITION,
  MGRILL_PROXIMITY,
} from "../constants";

import type { RemoteCursor as RemoteCursorType } from "../hooks/useMultiplayer";
import type { RemotePlayer } from "../hooks/useMultiplayer";
import type { ConnectionStatus } from "../hooks/useMultiplayer";
import type { SceneWorkerEntry } from "../hooks/useSceneWorkers";
import type {
  ClaudeUsageResponse,
  CursorPosition,
  PlotSlot,
  FloatingNumber,
  PlayerDirection,
  PlayerPosition,
  WorldDecoration,
} from "../types";
import GardenPanel from "./GardenPanel";
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
  /** Maximum garden plot count. */
  maxWorkers: number;
  /** Pre-computed garden plot positions. */
  plotSlots: PlotSlot[];
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

  // -- Multiplayer grill campfire --
  /** Whether the multiplayer grill overlay is currently open. */
  mgrillOpen: boolean;
  /** Called when the player clicks the campfire to open the grill overlay. */
  onMGrillOpen: () => void;
  /** Whether the multiplayer grill feature is enabled (hides sprite when false). */
  mgrillEnabled?: boolean;
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function HandWorldScene({
  sceneRef,
  sceneStyle,
  maxWorkers,
  plotSlots,
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
  mgrillOpen,
  onMGrillOpen,
  mgrillEnabled = false,
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

  // Proximity check: is the player near the mgrill campfire?
  const mgrillCenterX = MGRILL_POSITION.left + 3;
  const mgrillCenterY = MGRILL_POSITION.top + 3;
  const nearMGrill = useMemo(() => {
    if (!mgrillEnabled) return false;
    const dx = playerPosition.x - mgrillCenterX;
    const dy = playerPosition.y - mgrillCenterY;
    return Math.sqrt(dx * dx + dy * dy) < MGRILL_PROXIMITY;
  }, [
    mgrillEnabled,
    playerPosition.x,
    playerPosition.y,
    mgrillCenterX,
    mgrillCenterY,
  ]);

  // Build minimap worker positions from desk slot centers.
  const minimapWorkers: MinimapWorker[] = workerEntries
    .filter((w) => w.phase === "active" || w.phase === "walking-to-plot")
    .map((w) => ({ taskId: w.taskId, x: w.plot.left + 4, y: w.plot.top + 3.5 }));

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
      className={`card hand-world-card${nearArcade && !arcadeOpen ? " arcade-glow" : ""}${
        nearMGrill && !mgrillOpen ? " mgrill-glow" : ""
      }`}
      onClick={
        nearArcade && !arcadeOpen
          ? onArcadeOpen
          : nearMGrill && !mgrillOpen
          ? onMGrillOpen
          : undefined
      }
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
        <p>{maxWorkers} garden plots &middot; click a gardener to stream its output</p>
      </header>

      <div className="hand-world-layout">
      <div
        ref={sceneRef}
        className={`world-scene office-scene${selectedDecoEmoji ? " deco-placing" : ""}`}
        role="list"
        aria-label="Zen garden workers"
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
          <div className="zen-aurora" />
          <div className="zen-aurora zen-aurora-2" />
          <div className="zen-stars">
            <span className="star star-1" />
            <span className="star star-2" />
            <span className="star star-3" />
            <span className="star star-4" />
            <span className="star star-5" />
            <span className="star star-6" />
            <span className="star star-7" />
            <span className="star star-8" />
            <span className="star star-9" />
            <span className="star star-10" />
            <span className="star star-11" />
            <span className="star star-12" />
            <span className="star star-13" />
            <span className="star star-14" />
            <span className="star star-15" />
            <span className="star star-16" />
          </div>
          <div className="zen-constellation" />
          <div className="zen-mountain zen-mountain-1" />
          <div className="zen-mountain zen-mountain-2" />
          <div className="zen-mountain zen-mountain-3" />
          <div className="zen-moon">
            <span className="moon-halo" />
            <span className="moon-crater moon-crater-1" />
            <span className="moon-crater moon-crater-2" />
            <span className="moon-rays" />
          </div>
          <div className="zen-shooting-star" />
          <div className="zen-shooting-star zen-shooting-star-2" />
          <div className="zen-shooting-star zen-shooting-star-3" />
          <div className="zen-cloud zen-cloud-1" />
          <div className="zen-cloud zen-cloud-2" />
          <div className="zen-cloud zen-cloud-3" />
        </div>

        {/* Ground mist layer */}
        <div className="zen-mist" aria-hidden="true">
          <span className="mist-wisp mist-wisp-1" />
          <span className="mist-wisp mist-wisp-2" />
          <span className="mist-wisp mist-wisp-3" />
          <span className="mist-wisp mist-wisp-4" />
        </div>

        {/* Atmospheric particles */}
        <div className="zen-fireflies" aria-hidden="true">
          <span className="firefly firefly-1" />
          <span className="firefly firefly-2" />
          <span className="firefly firefly-3" />
          <span className="firefly firefly-4" />
          <span className="firefly firefly-5" />
          <span className="firefly firefly-6" />
          <span className="firefly firefly-7" />
          <span className="firefly firefly-8" />
          <span className="firefly firefly-9" />
          <span className="firefly firefly-10" />
        </div>
        <div className="zen-petals" aria-hidden="true">
          <span className="petal petal-1" />
          <span className="petal petal-2" />
          <span className="petal petal-3" />
          <span className="petal petal-4" />
          <span className="petal petal-5" />
          <span className="petal petal-6" />
          <span className="petal petal-7" />
          <span className="petal petal-8" />
          <span className="petal petal-9" />
          <span className="petal petal-10" />
          <span className="petal petal-11" />
          <span className="petal petal-12" />
        </div>

        {/* Sparkle dust particles */}
        <div className="zen-sparkles" aria-hidden="true">
          <span className="sparkle sparkle-1" />
          <span className="sparkle sparkle-2" />
          <span className="sparkle sparkle-3" />
          <span className="sparkle sparkle-4" />
          <span className="sparkle sparkle-5" />
          <span className="sparkle sparkle-6" />
          <span className="sparkle sparkle-7" />
          <span className="sparkle sparkle-8" />
        </div>

        {/* Garden decorations */}
        <div className="zen-gravel-path" aria-hidden="true" />
        <div className="zen-bamboo" aria-hidden="true">
          <span className="bamboo-stalk bamboo-stalk-1" />
          <span className="bamboo-stalk bamboo-stalk-2" />
          <span className="bamboo-stalk bamboo-stalk-3" />
          <span className="bamboo-leaves" />
        </div>
        <div className="zen-wisteria" aria-hidden="true">
          <span className="wisteria-trunk" />
          <span className="wisteria-branch wisteria-branch-1" />
          <span className="wisteria-branch wisteria-branch-2" />
          <span className="wisteria-drape wisteria-drape-1" />
          <span className="wisteria-drape wisteria-drape-2" />
          <span className="wisteria-drape wisteria-drape-3" />
          <span className="wisteria-drape wisteria-drape-4" />
          <span className="wisteria-drape wisteria-drape-5" />
          <span className="wisteria-glow" />
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
        <div className="zen-lantern zen-lantern-2" aria-hidden="true">
          <span className="lantern-cap" />
          <span className="lantern-light" />
          <span className="lantern-base" />
          <span className="lantern-glow" />
        </div>
        <div className="zen-rock zen-rock-lg" aria-hidden="true" />
        <div className="zen-rock zen-rock-sm" aria-hidden="true" />
        <div className="zen-rock zen-rock-moss" aria-hidden="true" />
        <div className="zen-pond zen-pond-1" aria-hidden="true">
          <span className="pond-water" />
          <span className="pond-algae pond-algae-1" />
          <span className="pond-algae pond-algae-2" />
          <span className="pond-ripple pond-ripple-1" />
          <span className="pond-ripple pond-ripple-2" />
          <span className="pond-shimmer" />
          <span className="pond-koi pond-koi-1" />
          <span className="pond-koi pond-koi-2" />
          <span className="pond-lilypad pond-lilypad-1" />
          <span className="pond-lilypad pond-lilypad-2" />
        </div>
        <div className="zen-pond zen-pond-2" aria-hidden="true">
          <span className="pond-water" />
          <span className="pond-algae pond-algae-1" />
          <span className="pond-ripple pond-ripple-1" />
          <span className="pond-shimmer" />
        </div>
        <div className="zen-pond zen-pond-3" aria-hidden="true">
          <span className="pond-water" />
          <span className="pond-algae pond-algae-1" />
          <span className="pond-algae pond-algae-2" />
          <span className="pond-ripple pond-ripple-1" />
          <span className="pond-ripple pond-ripple-2" />
          <span className="pond-shimmer" />
        </div>
        <div className="zen-pond zen-pond-4" aria-hidden="true">
          <span className="pond-water" />
          <span className="pond-algae pond-algae-1" />
          <span className="pond-ripple pond-ripple-1" />
        </div>

        {/* Stone bridge over path */}
        <div className="zen-bridge" aria-hidden="true">
          <span className="bridge-plank bridge-plank-1" />
          <span className="bridge-plank bridge-plank-2" />
          <span className="bridge-plank bridge-plank-3" />
          <span className="bridge-rail bridge-rail-left" />
          <span className="bridge-rail bridge-rail-right" />
        </div>

        {/* Stepping stones */}
        <span className="zen-stepping-stone zen-step-1" aria-hidden="true" />
        <span className="zen-stepping-stone zen-step-2" aria-hidden="true" />
        <span className="zen-stepping-stone zen-step-3" aria-hidden="true" />

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

        {/* Multiplayer grill campfire (bottom-centre) */}
        {mgrillEnabled && (
          <div
            className={`hh-mgrill-campfire${nearMGrill ? " mgrill-active" : ""}`}
            style={{ left: `${MGRILL_POSITION.left}%`, top: `${MGRILL_POSITION.top}%` }}
            aria-hidden="true"
          >
            <span className="mgrill-logs" />
            <span className="mgrill-flame mgrill-flame-1" />
            <span className="mgrill-flame mgrill-flame-2" />
            <span className="mgrill-flame mgrill-flame-3" />
            <span className="mgrill-ember mgrill-ember-1" />
            <span className="mgrill-ember mgrill-ember-2" />
            <div className="mgrill-label">GRILL</div>
            {nearMGrill && !mgrillOpen && (
              <div className="mgrill-prompt">Press to gather round!</div>
            )}
          </div>
        )}

        {/* Torii gate entrance (middle-left) */}
        <div className="hh-torii" aria-hidden="true">
          <span className="torii-pillar torii-pillar-left" />
          <span className="torii-pillar torii-pillar-right" />
          <span className="torii-kasagi" />
          <span className="torii-nuki" />
          <span className="torii-glow" />
          <div className="torii-label">ENTER</div>
        </div>

        {plotSlots.map((slot, slotIdx) => {
          const occupant = workerEntries.find((w) => w.slot === slotIdx);
          const showBonsai = occupant && (occupant.phase === "walking-to-plot" || occupant.phase === "active" || occupant.phase === "meditating" || occupant.phase === "fading");
          return (
            <div
              key={slot.id}
              className="garden-plot"
              style={{ left: `${slot.left}%`, top: `${slot.top}%` }}
              aria-hidden="true"
            >
              {showBonsai && (
                <span className={`plot-bonsai${occupant.phase === "active" ? " bonsai-growing" : ""}`}>
                  <span className="bonsai-pot" />
                  <span className="bonsai-trunk" />
                  <span className="bonsai-canopy bonsai-canopy-1" />
                  <span className="bonsai-canopy bonsai-canopy-2" />
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
            plotLeft={worker.plot.left}
            plotTop={worker.plot.top}
            task={{
              backend: worker.task?.backend,
              repoPath: worker.task?.repoPath,
              status: worker.task?.status,
            }}
            lastOutputLine={worker.lastOutputLine}
            schedule={worker.schedule}
            floatingNumbers={floatingNumbers.filter(
              (f) => f.taskId === worker.taskId,
            )}
            onSelect={onSelectTask}
          />
        ))}
      </div>

      <div className={`hand-world-side-panel${sidePanelOpen ? " open" : ""}`}>
        <GardenPanel
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
