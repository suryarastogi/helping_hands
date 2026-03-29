import { type CSSProperties, useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  buildDeskSlots,
  DEFAULT_CHARACTER_STYLE,
  DEFAULT_WORLD_MAX_WORKERS,
  PHASE_DURATION,
  providerFromBackend,
  PROVIDER_CHARACTER_DEFAULTS,
} from "../App.utils";
import type {
  DeskSlot,
  SceneWorker,
  SceneWorkerPhase,
  ScheduleItem,
  TaskHistoryItem,
  WorkerVariant,
} from "../types";

/** Enriched worker entry with task, desk, and style metadata for rendering. */
export type SceneWorkerEntry = SceneWorker & {
  task: TaskHistoryItem;
  desk: DeskSlot;
  isActive: boolean;
  provider: string;
  style: (typeof PROVIDER_CHARACTER_DEFAULTS)[string];
  spriteVariant: WorkerVariant;
  schedule: ScheduleItem | null;
};

export interface UseSceneWorkersOptions {
  /** All active tasks currently tracked. */
  activeTasks: TaskHistoryItem[];
  /** Set of active task IDs for fast lookup. */
  activeTaskIds: Set<string>;
  /** Map from taskId → TaskHistoryItem. */
  taskById: Map<string, TaskHistoryItem>;
  /** Fetched worker capacity from the server (may be null). */
  fetchedCapacity: number | null;
  /** All schedules, used to annotate workers with their schedule. */
  schedules: ScheduleItem[];
}

export function useSceneWorkers({
  activeTasks,
  activeTaskIds,
  taskById,
  fetchedCapacity,
  schedules,
}: UseSceneWorkersOptions) {
  const [sceneWorkers, setSceneWorkers] = useState<SceneWorker[]>([]);
  const [maxOfficeWorkers, setMaxOfficeWorkers] = useState(DEFAULT_WORLD_MAX_WORKERS);
  const slotByTaskRef = useRef<Record<string, number>>({});

  const deskSlots = useMemo(() => buildDeskSlots(maxOfficeWorkers), [maxOfficeWorkers]);

  const scheduleByTaskId = useMemo(() => {
    const map = new Map<string, ScheduleItem>();
    for (const s of schedules) {
      if (s.last_run_task_id) {
        map.set(s.last_run_task_id, s);
      }
    }
    return map;
  }, [schedules]);

  const claimSlotForTask = useCallback(
    (activeTaskId: string, occupiedSlots: Set<number>): number => {
      const existing = slotByTaskRef.current[activeTaskId];
      if (
        typeof existing === "number" &&
        existing >= 0 &&
        existing < maxOfficeWorkers &&
        !occupiedSlots.has(existing)
      ) {
        occupiedSlots.add(existing);
        return existing;
      }

      for (let slot = 0; slot < maxOfficeWorkers; slot += 1) {
        if (!occupiedSlots.has(slot)) {
          occupiedSlots.add(slot);
          slotByTaskRef.current[activeTaskId] = slot;
          return slot;
        }
      }

      slotByTaskRef.current[activeTaskId] = 0;
      occupiedSlots.add(0);
      return 0;
    },
    [maxOfficeWorkers],
  );

  const sceneWorkerEntries = useMemo<SceneWorkerEntry[]>(() => {
    return sceneWorkers.flatMap((worker) => {
      const task = taskById.get(worker.taskId);
      const desk = deskSlots[worker.slot];
      if (!task || !desk) return [];

      const provider = providerFromBackend(task.backend);
      const style =
        PROVIDER_CHARACTER_DEFAULTS[provider] ??
        PROVIDER_CHARACTER_DEFAULTS.other ??
        DEFAULT_CHARACTER_STYLE;

      return [
        {
          ...worker,
          task,
          desk,
          isActive: activeTaskIds.has(worker.taskId),
          provider,
          style,
          spriteVariant: provider === "goose" ? ("goose" as WorkerVariant) : style.variant,
          schedule: scheduleByTaskId.get(worker.taskId) ?? null,
        },
      ];
    });
  }, [activeTaskIds, deskSlots, scheduleByTaskId, sceneWorkers, taskById]);

  const officeDeskRows = useMemo(
    () => Math.max(1, Math.ceil(maxOfficeWorkers / 2)),
    [maxOfficeWorkers],
  );

  const worldSceneStyle = useMemo<CSSProperties>(() => {
    const extraRows = Math.max(0, officeDeskRows - 4);
    return { minHeight: `${380 + extraRows * 92}px` };
  }, [officeDeskRows]);

  // -- Capacity → max workers -----------------------------------------------
  useEffect(() => {
    setMaxOfficeWorkers((current) =>
      Math.max(
        current,
        fetchedCapacity ?? DEFAULT_WORLD_MAX_WORKERS,
        activeTasks.length,
        DEFAULT_WORLD_MAX_WORKERS,
      ),
    );
  }, [activeTasks.length, fetchedCapacity]);

  // -- Scene worker lifecycle -----------------------------------------------
  useEffect(() => {
    const now = Date.now();
    setSceneWorkers((current) => {
      const activeIds = new Set(activeTasks.map((item) => item.taskId));
      const existingByTaskId = new Map(current.map((worker) => [worker.taskId, worker]));
      const occupiedSlots = new Set<number>();
      const next: SceneWorker[] = [];

      for (const task of activeTasks) {
        const existing = existingByTaskId.get(task.taskId);
        const slot = claimSlotForTask(task.taskId, occupiedSlots);
        if (!existing) {
          next.push({ taskId: task.taskId, slot, phase: "at-factory", phaseChangedAt: now });
          continue;
        }
        if (existing.phase === "walking-to-exit" || existing.phase === "at-exit") {
          next.push({ ...existing, slot, phase: "at-factory", phaseChangedAt: now });
          continue;
        }
        if (existing.slot !== slot) {
          next.push({ ...existing, slot });
          continue;
        }
        next.push(existing);
      }

      for (const existing of current) {
        if (activeIds.has(existing.taskId)) continue;
        if (existing.phase === "walking-to-exit" || existing.phase === "at-exit") {
          next.push(existing);
          continue;
        }
        next.push({ ...existing, phase: "walking-to-exit", phaseChangedAt: now });
      }

      return next.sort((a, b) => a.slot - b.slot);
    });
  }, [activeTasks, claimSlotForTask]);

  // -- Scene worker phase timer ---------------------------------------------
  useEffect(() => {
    if (sceneWorkers.length === 0) return;

    const NEXT_PHASE: Partial<Record<SceneWorkerPhase, SceneWorkerPhase | null>> = {
      "at-factory": "walking-to-desk",
      "walking-to-desk": "active",
      "walking-to-exit": "at-exit",
      "at-exit": null,
    };

    const handle = window.setInterval(() => {
      const now = Date.now();
      setSceneWorkers((current) => {
        let hasChanges = false;
        const next: SceneWorker[] = [];

        for (const worker of current) {
          const elapsed = now - worker.phaseChangedAt;
          const duration = PHASE_DURATION[worker.phase];
          if (duration !== Infinity && elapsed >= duration) {
            const nextPhase = NEXT_PHASE[worker.phase];
            if (nextPhase === null || nextPhase === undefined) {
              delete slotByTaskRef.current[worker.taskId];
              hasChanges = true;
              continue;
            }
            next.push({ ...worker, phase: nextPhase, phaseChangedAt: now });
            hasChanges = true;
            continue;
          }
          next.push(worker);
        }

        return hasChanges ? next : current;
      });
    }, 100);

    return () => window.clearInterval(handle);
  }, [sceneWorkers.length]);

  return {
    sceneWorkers,
    maxOfficeWorkers,
    deskSlots,
    sceneWorkerEntries,
    worldSceneStyle,
  };
}
