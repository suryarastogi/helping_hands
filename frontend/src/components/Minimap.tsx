/**
 * Minimap — compact bird's-eye view of all players and workers in the scene.
 *
 * Renders a small fixed-size overlay showing coloured dots for the local
 * player, remote players, and active workers. Positions are normalised
 * against OFFICE_BOUNDS so the minimap matches the walkable area.
 */
import type { RemotePlayer } from "../hooks/useMultiplayer";
import type { PlayerPosition } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type MinimapWorker = {
  taskId: string;
  x: number;
  y: number;
};

export type MinimapProps = {
  /** Local player position (% of scene). */
  playerPosition: PlayerPosition;
  /** Connected remote players. */
  remotePlayers: RemotePlayer[];
  /** Active workers with scene positions. */
  workers: MinimapWorker[];
  /** Callback when the minimap is clicked — receives the target position in scene %. */
  onTeleport?: (position: PlayerPosition) => void;
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Minimap({
  playerPosition,
  remotePlayers,
  workers,
  onTeleport,
}: MinimapProps) {
  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!onTeleport) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    onTeleport({ x, y });
  };

  return (
    <div
      className={`minimap${onTeleport ? " minimap-clickable" : ""}`}
      aria-label="Minimap"
      onClick={handleClick}
      role={onTeleport ? "button" : undefined}
    >
      {/* Local player — white dot */}
      <span
        className="minimap-dot minimap-dot-local"
        style={{ left: `${playerPosition.x}%`, top: `${playerPosition.y}%` }}
        aria-label="You"
      />

      {/* Remote players — coloured dots */}
      {remotePlayers.map((rp) => (
        <span
          key={rp.player_id}
          className="minimap-dot minimap-dot-remote"
          style={{
            left: `${rp.x}%`,
            top: `${rp.y}%`,
            backgroundColor: rp.color,
          }}
          aria-label={rp.name}
        />
      ))}

      {/* Workers — amber dots */}
      {workers.map((w) => (
        <span
          key={w.taskId}
          className="minimap-dot minimap-dot-worker"
          style={{ left: `${w.x}%`, top: `${w.y}%` }}
          aria-label="Worker"
        />
      ))}
    </div>
  );
}
