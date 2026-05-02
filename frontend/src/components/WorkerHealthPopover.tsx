import type { WorkerHealthSnapshot } from "../types";

export interface WorkerHealthPopoverProps {
  snapshot: WorkerHealthSnapshot;
}

function classifyLoad(active: number, capacity: number): {
  color: string;
  label: string;
} {
  if (capacity <= 0) return { color: "var(--muted)", label: "unknown" };
  const ratio = active / capacity;
  if (ratio >= 1) return { color: "var(--danger)", label: "saturated" };
  if (ratio >= 0.75) return { color: "#f59e0b", label: "busy" };
  if (ratio > 0) return { color: "var(--success)", label: "running" };
  return { color: "var(--success)", label: "idle" };
}

export default function WorkerHealthPopover({
  snapshot,
}: WorkerHealthPopoverProps) {
  const { capacity, queue, inFlightTaskCount } = snapshot;
  const maxWorkers = capacity?.max_workers ?? 0;
  const active = queue?.active ?? inFlightTaskCount;
  const reserved = queue?.reserved ?? 0;
  const scheduled = queue?.scheduled ?? 0;
  const brokerDepth = queue?.broker_depth ?? 0;
  const backlog = brokerDepth + reserved + scheduled;
  const { color, label } = classifyLoad(active, maxWorkers);

  const perWorker = capacity?.workers ? Object.entries(capacity.workers) : [];

  return (
    <div className="worker-health-popover" role="dialog" aria-label="Worker health">
      <div className="worker-health-row worker-health-headline">
        <span className="worker-health-dot" style={{ backgroundColor: color }} />
        <span className="worker-health-headline-text">
          {active} / {maxWorkers || "?"} active
        </span>
        <span className="worker-health-status" style={{ color }}>
          {label}
        </span>
      </div>

      <div className="worker-health-row">
        <span className="worker-health-label">queue backlog</span>
        <span className="worker-health-value">{backlog}</span>
      </div>
      <div className="worker-health-row worker-health-subrow">
        <span className="worker-health-label">↳ broker waiting</span>
        <span className="worker-health-value">{brokerDepth}</span>
      </div>
      <div className="worker-health-row worker-health-subrow">
        <span className="worker-health-label">↳ reserved on workers</span>
        <span className="worker-health-value">{reserved}</span>
      </div>
      <div className="worker-health-row worker-health-subrow">
        <span className="worker-health-label">↳ scheduled (eta)</span>
        <span className="worker-health-value">{scheduled}</span>
      </div>

      {perWorker.length > 0 && (
        <>
          <div className="worker-health-divider" />
          <div className="worker-health-row worker-health-section">
            <span className="worker-health-label">per worker</span>
          </div>
          {perWorker.map(([name, slots]) => (
            <div key={name} className="worker-health-row worker-health-subrow">
              <span
                className="worker-health-label worker-health-worker-name"
                title={name}
              >
                {name}
              </span>
              <span className="worker-health-value">{slots} slots</span>
            </div>
          ))}
        </>
      )}

      <div className="worker-health-divider" />
      <div className="worker-health-row worker-health-source">
        <span className="worker-health-label">source</span>
        <span className="worker-health-value">
          cap: {capacity?.source ?? "—"} · queue: {queue?.source ?? "—"}
        </span>
      </div>
    </div>
  );
}
