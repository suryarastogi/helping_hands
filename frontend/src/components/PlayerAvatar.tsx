/**
 * PlayerAvatar — shared sprite component for the human player character.
 *
 * Renders the helmet/visor/torso/arms/legs/boots span-tree that was
 * previously duplicated between the local-player and remote-player
 * sections of the Hand World scene.
 */
import { type CSSProperties, useState } from "react";

import { EMOTE_MAP } from "../constants";
import type { PlayerDirection } from "../types";

export type PlayerAvatarProps = {
  /** Facing direction controls the CSS sprite orientation. */
  direction: PlayerDirection;
  /** Whether the walk animation is active. */
  walking: boolean;
  /** Display name shown above remote players (omitted for the local player). */
  name?: string;
  /** Current emote key (e.g. "wave") — rendered as a floating bubble. */
  emote?: string | null;
  /** Current chat message — rendered as a speech bubble above the avatar. */
  chat?: string | null;
  /** Whether the player is idle/AFK. */
  idle?: boolean;
  /** Whether the player is currently typing a chat message. */
  typing?: boolean;
  /** Avatar accent colour (used for remote-player CSS variables). */
  color?: string;
  /** True for the local (controlled) player; false for remote peers. */
  isLocal?: boolean;
  /** Position within the scene (% of scene dimensions). */
  x: number;
  y: number;
};

export default function PlayerAvatar({
  direction,
  walking,
  name,
  emote,
  chat,
  idle = false,
  typing = false,
  color,
  isLocal = false,
  x,
  y,
}: PlayerAvatarProps) {
  const className = isLocal
    ? `human-player ${direction}${walking ? " walking" : ""}`
    : `remote-player ${direction}${walking ? " walking" : ""}`;

  const style: CSSProperties = isLocal
    ? { left: `${x}%`, top: `${y}%` }
    : {
        left: `${x}%`,
        top: `${y}%`,
        "--rp-body": color,
        "--rp-accent": `${color}66`,
      } as CSSProperties;

  const [showTooltip, setShowTooltip] = useState(false);
  const ariaLabel = isLocal ? "You (player character)" : name;

  const statusLabel = typing
    ? "typing"
    : idle
      ? "idle"
      : walking
        ? "walking"
        : "active";

  return (
    <div
      className={className}
      style={style}
      aria-label={ariaLabel}
      onMouseEnter={!isLocal ? () => setShowTooltip(true) : undefined}
      onMouseLeave={!isLocal ? () => setShowTooltip(false) : undefined}
    >
      {!isLocal && name && (
        <span className="remote-player-name">{name}</span>
      )}
      {!isLocal && showTooltip && (
        <div className="player-tooltip" role="tooltip">
          <span className="player-tooltip-color" style={{ backgroundColor: color }} />
          <span className="player-tooltip-name">{name}</span>
          <span className={`player-tooltip-status player-tooltip-status-${statusLabel}`}>
            {statusLabel}
          </span>
        </div>
      )}
      {emote && (
        <span className="emote-bubble" aria-label={`Emote: ${emote}`}>
          {EMOTE_MAP[emote]}
        </span>
      )}
      {chat && (
        <span className="chat-bubble" aria-label={`Chat: ${chat}`}>
          {chat}
        </span>
      )}
      {typing && !emote && !chat && (
        <span className="typing-indicator" aria-label="Typing">
          ...
        </span>
      )}
      {idle && !typing && !emote && !chat && (
        <span className="idle-indicator" aria-label="Idle">
          zzz
        </span>
      )}
      <span className="human-shadow" />
      <span className="human-body">
        <span className="human-helmet" />
        <span className="human-helmet-light" />
        <span className="human-visor" />
        <span className="human-visor-shine" />
        <span className="human-torso" />
        <span className="human-belt" />
        <span className="human-buckle" />
        <span className="human-arm human-arm-left" />
        <span className="human-glove human-glove-left" />
        <span className="human-arm human-arm-right" />
        <span className="human-glove human-glove-right" />
        <span className="human-leg human-leg-left" />
        <span className="human-boot human-boot-left" />
        <span className="human-leg human-leg-right" />
        <span className="human-boot human-boot-right" />
      </span>
    </div>
  );
}
