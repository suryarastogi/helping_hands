/**
 * useSceneWorkers — manages the lifecycle of animated worker sprites in the
 * Hand World scene (factory → walking → desk → exit).
 *
 * Extracted from App.tsx to keep the main component focused on form/task state.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  DEFAULT_CHARACTER_STYLE,
  PHASE_DURATION,
  providerFromBackend,
  PROVIDER_CHARACTER_DEFAULTS,
} from "../App.utils";
import type {
  CharacterStyle,
  DeskSlot,
  FloatingNumber,
  SceneWorker,
  SceneWorkerPhase,
  ScheduleItem,
  TaskHistoryItem,
  WorkerVariant,
} from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SceneWorkerEntry = SceneWorker & {
  task: TaskHistoryItem;
  desk: DeskSlot;
  isActive: boolean;
  provider: string;
  style: CharacterStyle;
  spriteVariant: WorkerVariant;
  schedule: ScheduleItem | null;
};

export type UseSceneWorkersOptions = {
  activeTasks: TaskHistoryItem[];
  maxOfficeWorkers: number;
  deskSlots: DeskSlot[];
  taskHistory: TaskHistoryItem[];
  schedules: ScheduleItem[];
};

export type UseSceneWorkersReturn = {
  sceneWorkers: SceneWorker[];
  sceneWorkerEntries: SceneWorkerEntry[];
  floatingNumbers: FloatingNumber[];
  spawnFloatingNumber: (taskId: string, delta: number) => void;
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useSceneWorkers(options: UseSceneWorkersOptions): UseSceneWorkersReturn {
  const { activeTasks, maxOfficeWorkers, deskSlots, taskHistory, schedules } = options;

  const [sceneWorkers, setSceneWorkers] = useState<SceneWorker[]>([]);
  const slotByTaskRef = useRef<Record<string, number>>({});

  // Floating numbers (update count deltas shown above worker sprites).
  const [floatingNumbers, setFloatingNumbers] = useState<FloatingNumber[]>([]);
  const floatingIdRef = useRef(0);

  const spawnFloatingNumber = useCallback((forTaskId: string, delta: number) => {
    if (delta <= 0) return;
    const id = ++floatingIdRef.current;
    const now = Date.now();
    setFloatingNumbers((prev) => [...prev, { id, taskId: forTaskId, value: delta, createdAt: now }]);
    setTimeout(() => {
      setFloatingNumbers((prev) => prev.filter((f) => f.id !== id));
    }, 1200);
  }, []);

  // Stable set of active task IDs.
  const activeTaskIds = useMemo(
    () => new Set(activeTasks.map((task) => task.taskId)),
    [activeTasks],
  );

  // Lookup table: taskId → TaskHistoryItem.
  const taskById = useMemo(() => {
    const map = new Map<string, TaskHistoryItem>();
    for (const task of taskHistory) {
      map.set(task.taskId, task);
    }
    return map;
  }, [taskHistory]);

  // Lookup table: taskId → ScheduleItem (for tasks spawned by schedules).
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

  // Assign workers to active tasks and manage their phase lifecycle.
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
          next.push({
            taskId: task.taskId,
            slot,
            phase: "at-factory",
            phaseChangedAt: now,
          });
          continue;
        }
        if (existing.phase === "walking-to-exit" || existing.phase === "at-exit") {
          next.push({
            ...existing,
            slot,
            phase: "at-factory",
            phaseChangedAt: now,
          });
          continue;
        }
        if (existing.slot !== slot) {
          next.push({
            ...existing,
            slot,
          });
          continue;
        }
        next.push(existing);
      }

      for (const existing of current) {
        if (activeIds.has(existing.taskId)) {
          continue;
        }
        if (existing.phase === "walking-to-exit" || existing.phase === "at-exit") {
          next.push(existing);
          continue;
        }
        next.push({
          ...existing,
          phase: "walking-to-exit",
          phaseChangedAt: now,
        });
      }

      return next.sort((a, b) => a.slot - b.slot);
    });
  }, [activeTasks, claimSlotForTask]);

  // Phase transition timer — advances workers through their lifecycle.
  useEffect(() => {
    if (sceneWorkers.length === 0) {
      return;
    }

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
            next.push({
              ...worker,
              phase: nextPhase,
              phaseChangedAt: now,
            });
            hasChanges = true;
            continue;
          }
          next.push(worker);
        }

        return hasChanges ? next : current;
      });
    }, 100);

    return () => {
      window.clearInterval(handle);
    };
  }, [sceneWorkers.length]);

  // Build enriched worker entries for rendering.
  const sceneWorkerEntries = useMemo<SceneWorkerEntry[]>(() => {
    return sceneWorkers.flatMap((worker) => {
      const task = taskById.get(worker.taskId);
      const desk = deskSlots[worker.slot];
      if (!task || !desk) {
        return [];
      }

      const provider = providerFromBackend(task.backend);
      const style =
        PROVIDER_CHARACTER_DEFAULTS[provider] ?? PROVIDER_CHARACTER_DEFAULTS.other ?? DEFAULT_CHARACTER_STYLE;

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

  return {
    sceneWorkers,
    sceneWorkerEntries,
    floatingNumbers,
    spawnFloatingNumber,
  };
}
