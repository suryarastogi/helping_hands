/**
 * useWorkerHealth — polls worker capacity + queue depth + current tasks
 * and returns a single snapshot for the health-bar popover.
 *
 * Capacity is read on a 30s interval (cluster size changes rarely).
 * Queue depth and the current-task count are polled every 5s so the
 * popover reflects load in near-real-time without thrashing the broker.
 */
import { useEffect, useState } from "react";

import { apiUrl, fetchQueueDepth, fetchWorkerCapacityFull } from "../App.utils";
import type {
  CurrentTasksResponse,
  WorkerHealthSnapshot,
} from "../types";

export const WORKER_CAPACITY_POLL_MS = 30_000;
export const QUEUE_DEPTH_POLL_MS = 5_000;

async function fetchInFlightCount(): Promise<number | null> {
  try {
    const response = await fetch(apiUrl(`/tasks/current?_=${Date.now()}`), {
      cache: "no-store",
    });
    if (!response.ok) return null;
    const data = (await response.json()) as CurrentTasksResponse;
    return Array.isArray(data.tasks) ? data.tasks.length : 0;
  } catch {
    return null;
  }
}

export function useWorkerHealth(): WorkerHealthSnapshot {
  const [snapshot, setSnapshot] = useState<WorkerHealthSnapshot>({
    capacity: null,
    queue: null,
    inFlightTaskCount: 0,
  });

  useEffect(() => {
    let cancelled = false;

    const pollCapacity = async () => {
      const capacity = await fetchWorkerCapacityFull();
      if (cancelled) return;
      setSnapshot((prev) => ({ ...prev, capacity }));
    };

    const pollQueue = async () => {
      const [queue, inFlight] = await Promise.all([
        fetchQueueDepth(),
        fetchInFlightCount(),
      ]);
      if (cancelled) return;
      setSnapshot((prev) => ({
        ...prev,
        queue,
        inFlightTaskCount: inFlight ?? prev.inFlightTaskCount,
      }));
    };

    void pollCapacity();
    void pollQueue();
    const capHandle = window.setInterval(
      () => void pollCapacity(),
      WORKER_CAPACITY_POLL_MS,
    );
    const queueHandle = window.setInterval(
      () => void pollQueue(),
      QUEUE_DEPTH_POLL_MS,
    );

    return () => {
      cancelled = true;
      window.clearInterval(capHandle);
      window.clearInterval(queueHandle);
    };
  }, []);

  return snapshot;
}
