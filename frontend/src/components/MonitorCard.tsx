import type { Dispatch, LegacyRef, MouseEvent, RefObject, SetStateAction } from "react";

import type {
  AccumulatedUsage,
  InputItem,
  OutputTab,
  PrefixFilterMode,
} from "../types";
import {
  apiUrl,
  isTerminalTaskStatus,
  shortTaskId,
  statusBlinkerColor,
  statusTone,
} from "../App.utils";

export interface MonitorCardProps {
  taskId: string | null;
  issueNumber: number | null;
  status: string;
  taskError: { error: string; errorType: string } | null;
  isPolling: boolean;
  outputTab: OutputTab;
  onOutputTabChange: (tab: OutputTab) => void;
  prefixFilters: Record<string, PrefixFilterMode>;
  onPrefixFiltersChange: Dispatch<SetStateAction<Record<string, PrefixFilterMode>>>;
  activeOutputText: string;
  detectedPrefixes: string[];
  accUsage: AccumulatedUsage | null;
  taskInputs: InputItem[];
  runtimeDisplay: string | null;
  monitorOutputRef: RefObject<HTMLPreElement> | LegacyRef<HTMLPreElement>;
  monitorHeight: number | null;
  onMonitorScroll: () => void;
  onResizeStart: (e: MouseEvent) => void;
}

export default function MonitorCard({
  taskId,
  issueNumber,
  status,
  taskError,
  isPolling,
  outputTab,
  onOutputTabChange,
  prefixFilters,
  onPrefixFiltersChange,
  activeOutputText,
  detectedPrefixes,
  accUsage,
  taskInputs,
  runtimeDisplay,
  monitorOutputRef,
  monitorHeight,
  onMonitorScroll,
  onResizeStart,
}: MonitorCardProps) {
  const blinkerColor = statusBlinkerColor(status);
  const isBlinkerAnimated = statusTone(status) === "run";

  return (
    <section className="card status-card compact-monitor">
      <div className="monitor-bar">
        <div className="monitor-bar-left">
          <h2 className="monitor-title">Output{taskId ? `: ${shortTaskId(taskId)}` : ""}{issueNumber != null && (
            <span className="issue-badge" title={`Linked to GitHub issue #${issueNumber}`}> #{issueNumber}</span>
          )}</h2>
          <div className="pane-tabs" role="tablist" aria-label="Output mode">
            <button
              type="button"
              role="tab"
              className={`tab-btn${outputTab === "updates" ? " active" : ""}`}
              aria-selected={outputTab === "updates"}
              onClick={() => onOutputTabChange("updates")}
            >
              Updates
            </button>
            <button
              type="button"
              role="tab"
              className={`tab-btn${outputTab === "raw" ? " active" : ""}`}
              aria-selected={outputTab === "raw"}
              onClick={() => onOutputTabChange("raw")}
            >
              Raw
            </button>
            <button
              type="button"
              role="tab"
              className={`tab-btn${outputTab === "payload" ? " active" : ""}`}
              aria-selected={outputTab === "payload"}
              onClick={() => onOutputTabChange("payload")}
            >
              Payload
            </button>
          </div>
        </div>
        <div className="monitor-bar-right">
          {taskId && !isTerminalTaskStatus(status) && (
            <button
              type="button"
              className="secondary cancel-task-btn"
              style={{ fontSize: "0.7rem", padding: "2px 8px", color: "#fca5a5", borderColor: "#7f1d1d" }}
              title="Cancel this task"
              onClick={async () => {
                if (!confirm("Cancel this task?")) return;
                try {
                  await fetch(apiUrl(`/tasks/${taskId}/cancel`), { method: "POST" });
                } catch {
                  /* swallow — next poll picks up REVOKED */
                }
              }}
            >
              Cancel
            </button>
          )}
          <button
            type="button"
            className="secondary"
            style={{ fontSize: "0.7rem", padding: "2px 8px" }}
            title="Copy output to clipboard"
            onClick={() => {
              navigator.clipboard.writeText(activeOutputText).catch(() => {});
            }}
          >
            Copy
          </button>
          <span
            className={`status-blinker${isBlinkerAnimated ? " pulse" : ""}`}
            style={{ backgroundColor: blinkerColor }}
            title={`${status}${isPolling ? " (polling)" : ""}`}
          />
          {runtimeDisplay && (
            <span className="elapsed-timer" title="Elapsed runtime">
              {runtimeDisplay}
            </span>
          )}
          <span className="info-badge" title={taskId || "No task selected"}>
            i
          </span>
        </div>
      </div>
      {(accUsage || (detectedPrefixes.length > 0 && outputTab !== "payload")) && (
        <div className="prefix-filters">
          {detectedPrefixes.length > 0 && outputTab !== "payload" && (
            <>
              <span className="prefix-filters-label">Filter:</span>
              {detectedPrefixes.map((prefix) => {
                const mode = prefixFilters[prefix] ?? "show";
                return (
                  <button
                    key={prefix}
                    type="button"
                    className={`prefix-chip ${mode}`}
                    title={`[${prefix}] — ${mode === "show" ? "Showing (click to hide)" : mode === "hide" ? "Hidden (click for only)" : "Only (click to reset)"}`}
                    onClick={() => {
                      onPrefixFiltersChange((prev) => {
                        const current = prev[prefix] ?? "show";
                        const next: PrefixFilterMode =
                          current === "show" ? "hide" : current === "hide" ? "only" : "show";
                        const updated = { ...prev };
                        if (next === "show") {
                          delete updated[prefix];
                        } else {
                          updated[prefix] = next;
                        }
                        return updated;
                      });
                    }}
                  >
                    <span className="prefix-chip-icon">
                      {mode === "show" ? "●" : mode === "hide" ? "○" : "◉"}
                    </span>
                    [{prefix}]
                  </button>
                );
              })}
              {Object.keys(prefixFilters).length > 0 && (
                <button
                  type="button"
                  className="prefix-chip reset"
                  title="Reset all filters"
                  onClick={() => onPrefixFiltersChange({})}
                >
                  Reset
                </button>
              )}
            </>
          )}
          {accUsage && (
            <span
              className="usage-total"
              title={`${accUsage.count} API call${accUsage.count !== 1 ? "s" : ""}, ${Math.round(accUsage.totalSeconds)}s, in=${accUsage.totalIn.toLocaleString()} out=${accUsage.totalOut.toLocaleString()}`}
            >
              api: ${accUsage.totalCost.toFixed(4)}, {Math.round(accUsage.totalSeconds)}s, in={accUsage.totalIn.toLocaleString()} out={accUsage.totalOut.toLocaleString()}
            </span>
          )}
        </div>
      )}
      {taskError && (
        <div className="task-error-banner">
          <strong>{taskError.errorType}</strong>
          <code>{taskError.error}</code>
        </div>
      )}
      <pre
        ref={monitorOutputRef as LegacyRef<HTMLPreElement>}
        className="monitor-output"
        onScroll={onMonitorScroll}
        style={monitorHeight != null ? { height: monitorHeight, minHeight: 60, maxHeight: "none" } : undefined}
      >{activeOutputText}</pre>
      <div className="monitor-resize-handle" onMouseDown={onResizeStart} title="Drag to resize" />

      <details className="compact-advanced monitor-inputs">
        <summary>Task inputs</summary>
        <div className="compact-advanced-body">
          {taskInputs.length === 0 ? (
            <p className="inputs-empty">Inputs not available yet.</p>
          ) : (
            <dl className="inputs-grid">
              {taskInputs.map((item) => (
                <div key={item.label} className="input-item">
                  <dt>{item.label}</dt>
                  <dd>{item.value}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </details>
    </section>
  );
}
