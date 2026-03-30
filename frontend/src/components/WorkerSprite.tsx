/**
 * WorkerSprite — renders an animated worker character in the Hand World scene.
 *
 * Two visual variants: "goose" (the Goose CLI backend) and bot sprites
 * (bot-alpha, bot-round, bot-heavy) for all other backends. Each variant
 * is built from positioned `<span>` elements with inline colour styles
 * derived from the backend's CharacterStyle.
 */
import { FACTORY_POS, INCINERATOR_POS } from "../constants";
import type {
  CharacterStyle,
  FloatingNumber,
  SceneWorkerPhase,
  WorkerVariant,
} from "../types";
import { cronFrequency, formatInterval, formatProviderName, repoName } from "../App.utils";

export type WorkerSpriteProps = {
  taskId: string;
  phase: SceneWorkerPhase;
  style: CharacterStyle;
  spriteVariant: WorkerVariant;
  isActive: boolean;
  isSelected: boolean;
  provider: string;
  deskLeft: number;
  deskTop: number;
  task: {
    backend?: string | null;
    repoPath?: string | null;
    status?: string;
  };
  schedule: {
    name: string;
    schedule_type?: string;
    cron_expression: string;
    interval_seconds?: number | null;
  } | null;
  floatingNumbers: FloatingNumber[];
  onSelect: (taskId: string) => void;
};

export default function WorkerSprite({
  taskId,
  phase,
  style: workerStyle,
  spriteVariant,
  isActive,
  isSelected,
  provider,
  deskLeft,
  deskTop,
  task,
  schedule,
  floatingNumbers,
  onSelect,
}: WorkerSpriteProps) {
  const isAtFactory = phase === "at-factory";
  const isAtExit = phase === "walking-to-exit" || phase === "at-exit";
  const posLeft = isAtFactory
    ? FACTORY_POS.left
    : isAtExit
      ? INCINERATOR_POS.left
      : deskLeft;
  const posTop = isAtFactory
    ? FACTORY_POS.top
    : isAtExit
      ? INCINERATOR_POS.top
      : deskTop;

  return (
    <button
      type="button"
      role="listitem"
      className={`worker-sprite ${phase}${isSelected ? " selected" : ""}`}
      style={{ left: `${posLeft}%`, top: `${posTop}%` }}
      onClick={() => onSelect(taskId)}
      title={`${task.backend ?? "unknown"} • ${taskId}${task.repoPath ? ` • ${task.repoPath}` : ""}${schedule ? ` • ${schedule.name} (${schedule.schedule_type === "interval" && schedule.interval_seconds ? `every ${formatInterval(schedule.interval_seconds)}` : schedule.cron_expression})` : ""}`}
      disabled={!isActive}
    >
      <span className={`worker-art ${spriteVariant}`} aria-hidden="true">
        <span className="sprite-shadow" />
        {spriteVariant === "goose" ? (
          <GooseBody style={workerStyle} />
        ) : (
          <BotBody style={workerStyle} />
        )}
      </span>
      {floatingNumbers.map((f) => (
        <span key={f.id} className="floating-number" aria-hidden="true">
          +{f.value}
        </span>
      ))}
      <span className="worker-caption">
        {task.repoPath && (
          <span className="worker-repo">{repoName(task.repoPath)}</span>
        )}
        <span>
          {formatProviderName(provider)} • {task.status ?? "unknown"}
        </span>
        {schedule &&
          (() => {
            if (schedule.schedule_type === "interval" && schedule.interval_seconds) {
              const label = formatInterval(schedule.interval_seconds);
              return (
                <span
                  className="worker-cron"
                  title={`Schedule: ${schedule.name} (every ${label}, non-concurrent)`}
                >
                  {"\uD83D\uDD04"} {label}
                </span>
              );
            }
            const freq = cronFrequency(schedule.cron_expression);
            return freq ? (
              <span
                className="worker-cron"
                title={`Schedule: ${schedule.name} (${schedule.cron_expression})`}
              >
                {freq.symbol} {freq.label}
              </span>
            ) : null;
          })()}
      </span>
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Internal sub-components for each sprite variant                    */
/* ------------------------------------------------------------------ */

function GooseBody({ style: s }: { style: CharacterStyle }) {
  return (
    <>
      <span className="goose-tail" style={{ backgroundColor: s.bodyColor, borderColor: s.outlineColor }} />
      <span className="goose-body" style={{ backgroundColor: s.bodyColor, borderColor: s.outlineColor }} />
      <span className="goose-wing" style={{ backgroundColor: s.skinColor }} />
      <span className="goose-wing-tip" style={{ backgroundColor: s.bodyColor }} />
      <span className="goose-neck" style={{ backgroundColor: s.bodyColor, borderColor: s.outlineColor }} />
      <span className="goose-head" style={{ backgroundColor: s.bodyColor, borderColor: s.outlineColor }} />
      <span className="goose-beak" style={{ backgroundColor: s.accentColor }} />
      <span className="goose-eye" style={{ backgroundColor: s.outlineColor }} />
      <span className="goose-brow" style={{ backgroundColor: s.outlineColor }} />
      <span className="goose-cheek" />
      <span className="goose-leg goose-leg-left" style={{ backgroundColor: s.accentColor }} />
      <span className="goose-leg goose-leg-right" style={{ backgroundColor: s.accentColor }} />
      <span className="goose-foot goose-foot-left" style={{ backgroundColor: s.accentColor }} />
      <span className="goose-foot goose-foot-right" style={{ backgroundColor: s.accentColor }} />
    </>
  );
}

function BotBody({ style: s }: { style: CharacterStyle }) {
  return (
    <>
      <span className="bot-antenna" style={{ backgroundColor: s.accentColor }} />
      <span className="bot-antenna-tip" style={{ backgroundColor: s.accentColor }} />
      <span className="bot-ear bot-ear-left" style={{ backgroundColor: s.bodyColor, borderColor: s.outlineColor }} />
      <span className="bot-ear bot-ear-right" style={{ backgroundColor: s.bodyColor, borderColor: s.outlineColor }} />
      <span className="bot-head" style={{ backgroundColor: s.skinColor, borderColor: s.outlineColor }} />
      <span className="bot-eye bot-eye-left" style={{ backgroundColor: s.accentColor }} />
      <span className="bot-eye bot-eye-right" style={{ backgroundColor: s.accentColor }} />
      <span className="bot-mouth" style={{ backgroundColor: s.accentColor }} />
      <span className="bot-torso" style={{ backgroundColor: s.bodyColor, borderColor: s.outlineColor }} />
      <span className="bot-core" style={{ backgroundColor: s.accentColor }} />
      <span className="bot-arm bot-arm-left" style={{ backgroundColor: s.bodyColor, borderColor: s.outlineColor }} />
      <span className="bot-arm bot-arm-right" style={{ backgroundColor: s.bodyColor, borderColor: s.outlineColor }} />
      <span className="bot-leg bot-leg-left" style={{ backgroundColor: s.outlineColor }} />
      <span className="bot-leg bot-leg-right" style={{ backgroundColor: s.outlineColor }} />
      <span className="bot-foot bot-foot-left" style={{ backgroundColor: s.outlineColor }} />
      <span className="bot-foot bot-foot-right" style={{ backgroundColor: s.outlineColor }} />
    </>
  );
}
