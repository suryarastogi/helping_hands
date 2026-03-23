import { useCallback, useEffect, useRef, useState } from "react";
import { shortTaskId, statusTone } from "../App.utils";
import type { ServiceHealthState } from "../types";

export interface AppOverlaysProps {
  serviceHealthState: ServiceHealthState | null;
  toasts: { id: number; taskId: string; status: string }[];
  onRemoveToast: (id: number) => void;
}

type HealthIndicator = {
  key: string;
  label: string;
  state: "ok" | "error" | "na" | null;
};

function buildHealthIndicators(
  serviceHealthState: ServiceHealthState | null,
): HealthIndicator[] {
  return [
    {
      key: "api",
      label: "api",
      state:
        serviceHealthState === null
          ? null
          : serviceHealthState.reachable
            ? "ok"
            : "error",
    },
    {
      key: "redis",
      label: "redis",
      state: serviceHealthState?.health?.redis ?? null,
    },
    {
      key: "db",
      label: "db",
      state: serviceHealthState?.health?.db ?? null,
    },
    {
      key: "workers",
      label: "workers",
      state: serviceHealthState?.health?.workers ?? null,
    },
  ];
}

export default function AppOverlays({
  serviceHealthState,
  toasts,
  onRemoveToast,
}: AppOverlaysProps) {
  const [notifPerm, setNotifPerm] = useState<NotificationPermission>(
    typeof Notification !== "undefined" ? Notification.permission : "denied",
  );

  const swReg = useRef<ServiceWorkerRegistration | null>(null);

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker
      .register("/notif-sw.js")
      .then((reg) => {
        swReg.current = reg;
        console.log("[HH] Notification SW registered");
      })
      .catch((err) => console.warn("[HH] SW registration failed:", err));
  }, []);

  const requestNotifPermission = useCallback(() => {
    if (typeof Notification === "undefined") return;
    Notification.requestPermission()
      .then((perm) => {
        setNotifPerm(perm);
      })
      .catch(() => {
        /* permission request failed or was dismissed */
      });
  }, []);

  const testNotification = useCallback(() => {
    if (typeof Notification === "undefined") {
      alert("Notification API not available in this context");
      return;
    }
    if (Notification.permission !== "granted") {
      Notification.requestPermission()
        .then((perm) => {
          setNotifPerm(perm);
          if (perm === "granted") testNotification();
        })
        .catch(() => {
          /* permission request failed or was dismissed */
        });
      return;
    }
    const body = "If you see this, OS notifications are working!";
    const reg = swReg.current;
    if (reg) {
      reg
        .showNotification("Helping Hands — Test", { body })
        .catch((err) => alert("showNotification failed: " + String(err)));
    } else {
      try {
        new Notification("Helping Hands — Test", { body });
      } catch (err) {
        alert("Notification failed: " + String(err));
      }
    }
  }, []);

  const serviceHealthIndicators = buildHealthIndicators(serviceHealthState);

  return (
    <>
      {notifPerm === "default" && (
        <div className="notif-banner">
          <span>Enable OS notifications for task updates?</span>
          <button onClick={requestNotifPermission}>Enable</button>
          <button onClick={() => setNotifPerm("denied")}>Dismiss</button>
        </div>
      )}
      {toasts.length > 0 && (
        <div className="toast-container">
          {toasts.map((t) => (
            <div
              key={t.id}
              className={`toast toast--${statusTone(t.status)}`}
            >
              <span className="toast-text">
                Task {shortTaskId(t.taskId)} — {t.status}
              </span>
              <button
                className="toast-close"
                onClick={() => onRemoveToast(t.id)}
                aria-label="Dismiss"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
      <div className="service-health-bar" aria-label="Service health">
        {serviceHealthIndicators
          .filter((item) => item.state !== "na")
          .map((item) => {
            const color =
              item.state === "ok"
                ? "var(--success)"
                : item.state === "error"
                  ? "var(--danger)"
                  : "#4b5563";
            const title =
              item.state === null
                ? `${item.label}: checking…`
                : `${item.label}: ${item.state}`;
            return (
              <span
                key={item.key}
                className="service-health-item"
                title={title}
              >
                <span
                  className={`service-health-dot${item.state === null ? " service-health-dot--checking" : ""}`}
                  style={{ backgroundColor: color }}
                />
                <span className="service-health-label">{item.label}</span>
              </span>
            );
          })}
        <button
          type="button"
          className="service-health-item"
          style={{
            cursor: "pointer",
            background: "none",
            border: "none",
            color: "inherit",
            fontSize: "inherit",
            padding: 0,
          }}
          onClick={testNotification}
          title="Send a test OS notification"
        >
          <span
            className="service-health-label"
            style={{ textDecoration: "underline", opacity: 0.7 }}
          >
            test notification
          </span>
        </button>
      </div>
    </>
  );
}
