/**
 * useServiceHealth — polls the backend service health endpoint every 15 seconds.
 *
 * Returns the latest `ServiceHealthState` (reachable + individual service status).
 */
import { useEffect, useState } from "react";

import { fetchServiceHealth } from "../App.utils";
import type { ServiceHealthState } from "../types";

/** Polling interval in milliseconds (15 s). */
export const SERVICE_HEALTH_POLL_MS = 15_000;

export function useServiceHealth(): ServiceHealthState | null {
  const [state, setState] = useState<ServiceHealthState | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      const result = await fetchServiceHealth();
      if (!cancelled) setState(result);
    };
    void check();
    const handle = window.setInterval(() => void check(), SERVICE_HEALTH_POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  return state;
}
