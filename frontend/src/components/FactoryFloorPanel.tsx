/**
 * FactoryFloorPanel — compact HUD overlay in Hand World.
 *
 * Shows station/worker counts, connection status, and the
 * shared decoration toolbar.
 */
import {
  DECORATION_EMOJIS,
  MAX_DECORATIONS,
} from "../constants";
import type { ConnectionStatus } from "../hooks/useMultiplayer";
import type { WorldDecoration } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type FactoryFloorPanelProps = {
  maxWorkers: number;
  activeWorkerCount: number;
  connectionStatus: ConnectionStatus;
  // -- Decorations --
  decorations: WorldDecoration[];
  onClearDecorations: () => void;
  decoOnCooldown: boolean;
  selectedDecoEmoji: string | null;
  onSelectedDecoEmojiChange: (emoji: string | null) => void;
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function FactoryFloorPanel({
  maxWorkers,
  activeWorkerCount,
  connectionStatus,
  decorations,
  onClearDecorations,
  decoOnCooldown,
  selectedDecoEmoji,
  onSelectedDecoEmojiChange,
}: FactoryFloorPanelProps) {
  return (
    <div className="zen-status-summary">
      <div className="status-summary-header">Factory Floor</div>
      <div className="status-summary-stat">
        <span className="stat-icon">&#128187;</span>
        <span>{maxWorkers} Stations</span>
      </div>
      <div className="status-summary-stat">
        <span className="stat-icon">&#129302;</span>
        <span>{activeWorkerCount} Active</span>
      </div>
      <div className="status-summary-hint">
        <span className={`conn-status-dot conn-status-${connectionStatus}`} aria-label={`Connection: ${connectionStatus}`} />
        {connectionStatus === "connected"
          ? "Multiplayer active"
          : connectionStatus === "connecting"
            ? "Connecting\u2026"
            : connectionStatus === "failed"
              ? "Connection failed"
              : "Disconnected"}
      </div>
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
                onClick={() => onSelectedDecoEmojiChange(selectedDecoEmoji === emoji ? null : emoji)}
                disabled={decorations.length >= MAX_DECORATIONS || decoOnCooldown}
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
  );
}
