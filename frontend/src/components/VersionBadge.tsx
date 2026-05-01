/**
 * VersionBadge — bottom-right badge showing the frontend version with a
 * status dot, plus a hover/click panel revealing per-component versions.
 *
 * Fires a one-time toast per session when an actually-deployed instance
 * shows a mismatch or tampering — the failure modes that matter.
 * Does nothing when running locally (status === "dev").
 */
import { useEffect, useMemo, useRef, useState } from "react";

import { useVersion, type VersionStatus } from "../hooks/useVersion";

const DOT_COLOR: Record<VersionStatus, string> = {
  loading: "#888",
  dev: "#888",
  match: "#3ddb6e",
  mismatch: "#ff5e5e",
  missing: "#f0a040",
  tampered: "#ff5e5e",
};

const STATUS_LABEL: Record<VersionStatus, string> = {
  loading: "Loading version…",
  dev: "Local development — versions are informational",
  match: "All components in sync",
  mismatch: "Version mismatch detected",
  missing: "Worker version unknown",
  tampered: "Backend code modified after deploy",
};

const TOAST_ID = "hh_version_toast_dismissed_v1";

function formatCommitDate(iso: string | null): string {
  if (!iso) return "unknown";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toISOString().replace("T", " ").slice(0, 19) + "Z";
  } catch {
    return iso;
  }
}

export default function VersionBadge() {
  const v = useVersion();
  const [open, setOpen] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [toastDismissed, setToastDismissed] = useState<boolean>(() => {
    try {
      return sessionStorage.getItem(TOAST_ID) === "1";
    } catch {
      return false;
    }
  });
  const toastFiredFor = useRef<string | null>(null);

  const showToast = useMemo(() => {
    if (toastDismissed) return false;
    if (v.status !== "mismatch" && v.status !== "tampered") return false;
    return true;
  }, [v.status, toastDismissed]);

  // Track which (status, backend, workers-fingerprint) combo has been toasted
  // so we don't keep re-firing on re-renders.
  const fingerprint = `${v.status}|${v.backend ?? ""}|${Object.entries(v.workers).sort().join(",")}`;
  useEffect(() => {
    if (showToast && toastFiredFor.current !== fingerprint) {
      toastFiredFor.current = fingerprint;
    }
  }, [showToast, fingerprint]);

  const handleCopy = () => {
    try {
      void navigator.clipboard?.writeText(v.frontend);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      // ignore
    }
  };

  const dismissToast = () => {
    setToastDismissed(true);
    try {
      sessionStorage.setItem(TOAST_ID, "1");
    } catch {
      // ignore
    }
  };

  const dotColor = DOT_COLOR[v.status];
  const tooltip = STATUS_LABEL[v.status];

  const toastMessage =
    v.status === "tampered"
      ? `Backend code was modified after deploy — running ${v.backend ?? "?"}, deployed ${v.sentinelSha?.slice(0, 7) ?? "?"}.`
      : `Components disagree: FE ${v.frontend} · BE ${v.backend ?? "?"} · W ${
          Object.keys(v.workers).length === 0
            ? "(none registered)"
            : Object.values(v.workers).join(", ")
        }`;

  return (
    <>
      <div
        className="version-badge"
        style={{
          position: "fixed",
          bottom: 8,
          right: 8,
          zIndex: 9999,
          background: "rgba(20, 20, 24, 0.85)",
          color: "#ddd",
          fontFamily:
            "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          fontSize: 11,
          padding: "4px 8px",
          borderRadius: 4,
          border: "1px solid rgba(255,255,255,0.1)",
          cursor: "pointer",
          userSelect: "none",
        }}
        onClick={() => {
          setOpen((o) => !o);
          handleCopy();
        }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        title={tooltip}
        data-testid="version-badge"
      >
        <span
          aria-hidden="true"
          style={{
            display: "inline-block",
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: dotColor,
            marginRight: 6,
            verticalAlign: "middle",
          }}
        />
        <span style={{ verticalAlign: "middle" }}>
          {v.frontend}
          {copied ? " ✓" : ""}
        </span>
        {open && (
          <div
            style={{
              position: "absolute",
              bottom: "100%",
              right: 0,
              marginBottom: 6,
              background: "rgba(20, 20, 24, 0.95)",
              border: "1px solid rgba(255,255,255,0.15)",
              borderRadius: 4,
              padding: "8px 10px",
              minWidth: 280,
              lineHeight: 1.5,
              cursor: "default",
            }}
          >
            <div style={{ marginBottom: 4, color: "#fff" }}>
              <strong>{tooltip}</strong>
            </div>
            <div>
              <span style={{ color: "#888" }}>Frontend</span>: {v.frontend}
            </div>
            <div>
              <span style={{ color: "#888" }}>Backend</span>:{" "}
              {v.backend ?? <em>unreachable</em>}
            </div>
            <div>
              <span style={{ color: "#888" }}>Worker(s)</span>:{" "}
              {Object.keys(v.workers).length === 0 ? (
                <em>none registered</em>
              ) : (
                Object.entries(v.workers).map(([host, ver]) => (
                  <div key={host} style={{ paddingLeft: 8 }}>
                    {host}: {ver}
                  </div>
                ))
              )}
            </div>
            <div style={{ marginTop: 6, color: "#888" }}>
              <div>SHA: {v.gitSha ?? "unknown"}</div>
              <div>Commit: {formatCommitDate(v.commitDate)}</div>
              {v.isDeployed && v.sentinelSha && (
                <div>Deployed SHA: {v.sentinelSha}</div>
              )}
            </div>
          </div>
        )}
      </div>
      {showToast && (
        <div
          role="alert"
          data-testid="version-mismatch-toast"
          style={{
            position: "fixed",
            bottom: 50,
            right: 8,
            zIndex: 9999,
            background: "#3a1518",
            color: "#ffd9d9",
            padding: "10px 12px",
            border: "1px solid #ff5e5e",
            borderRadius: 4,
            maxWidth: 360,
            fontSize: 12,
            lineHeight: 1.4,
            boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4 }}>
            ⚠ {STATUS_LABEL[v.status]}
          </div>
          <div>{toastMessage}</div>
          <button
            type="button"
            onClick={dismissToast}
            style={{
              marginTop: 6,
              background: "transparent",
              color: "#ffd9d9",
              border: "1px solid #ff5e5e",
              padding: "2px 8px",
              borderRadius: 3,
              cursor: "pointer",
            }}
          >
            Dismiss
          </button>
        </div>
      )}
    </>
  );
}
