/**
 * useOnboarding — Tracks first-visit state and idle detection to drive a
 * guided tutorial overlay.  When the user is idle for ONBOARDING_IDLE_MS
 * without any active/scheduled tasks, the next tutorial step is highlighted.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ONBOARDING_STORAGE_KEY = "hh_onboarding_completed";
const ONBOARDING_DISMISSED_KEY = "hh_onboarding_dismissed";

/** Idle threshold before showing the next tutorial hint. */
export const ONBOARDING_IDLE_MS = 5_000;

/** Base tutorial steps every user sees. */
const BASE_STEPS: OnboardingStep[] = [
  {
    id: "new-task",
    target: ".new-submission-button",
    title: "Create your first task",
    body: "Click here to open the task form. Enter a repo and a prompt to kick off an AI-powered build.",
    placement: "right",
  },
  {
    id: "repo-input",
    target: ".repo-suggest-wrapper",
    title: "Choose a repository",
    body: "Type an owner/repo (e.g. octocat/Hello-World) or a local path. We\u2019ll clone it automatically.",
    placement: "bottom",
  },
  {
    id: "prompt-input",
    target: ".prompt-input",
    title: "Describe your task",
    body: "Tell the AI what to build or fix \u2014 e.g. \u201CAdd dark mode support\u201D or \u201CFix the login bug\u201D.",
    placement: "bottom",
  },
  {
    id: "submit-btn",
    target: ".submit-inline",
    title: "Run it!",
    body: "Hit Run to submit your task. The AI will clone the repo, make changes, and open a PR.",
    placement: "bottom",
  },
  {
    id: "schedules",
    target: ".new-submission-button + .new-submission-button",
    title: "Schedule recurring tasks",
    body: "Set up cron or interval schedules to run tasks automatically \u2014 like nightly lint fixes.",
    placement: "right",
  },
];

/** Extra step shown when the server has no GITHUB_TOKEN env var. */
const GITHUB_TOKEN_STEP: OnboardingStep = {
  id: "github-token",
  target: ".github-token-input",
  title: "Add a GitHub token",
  body: "The server doesn\u2019t have a GITHUB_TOKEN configured. Open Advanced and paste a personal access token so tasks can push branches and open PRs.",
  placement: "bottom",
};

export type OnboardingStep = {
  id: string;
  target: string;
  title: string;
  body: string;
  placement: "right" | "bottom";
};

/** Build the step list, injecting the token step after prompt if needed. */
export function buildOnboardingSteps(serverHasGithubToken: boolean): OnboardingStep[] {
  if (serverHasGithubToken) return BASE_STEPS;
  // Insert the token step right before the submit button
  const idx = BASE_STEPS.findIndex((s) => s.id === "submit-btn");
  const steps = [...BASE_STEPS];
  steps.splice(idx, 0, GITHUB_TOKEN_STEP);
  return steps;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface UseOnboardingReturn {
  /** Whether the onboarding tutorial is currently active/visible. */
  isActive: boolean;
  /** Index into ONBOARDING_STEPS for the current step (null if inactive). */
  currentStepIndex: number | null;
  /** The current step definition, or null. */
  currentStep: OnboardingStep | null;
  /** Advance to the next step (or finish if on the last). */
  nextStep: () => void;
  /** Go back to the previous step. */
  prevStep: () => void;
  /** Skip / dismiss the entire tutorial. */
  dismiss: () => void;
  /** Restart the tutorial (e.g. from a help menu). */
  restart: () => void;
  /** Total number of steps. */
  totalSteps: number;
}

export function useOnboarding({
  hasActiveTasks,
  hasSchedules,
  serverHasGithubToken,
}: {
  /** True when there are running or queued tasks. */
  hasActiveTasks: boolean;
  /** True when the user has at least one schedule configured. */
  hasSchedules: boolean;
  /** Whether the server has GITHUB_TOKEN set. */
  serverHasGithubToken: boolean;
}): UseOnboardingReturn {
  const steps = useMemo(
    () => buildOnboardingSteps(serverHasGithubToken),
    [serverHasGithubToken],
  );

  const [stepIndex, setStepIndex] = useState<number | null>(null);
  const [dismissed, setDismissed] = useState(() => {
    try {
      return (
        localStorage.getItem(ONBOARDING_STORAGE_KEY) === "true" ||
        localStorage.getItem(ONBOARDING_DISMISSED_KEY) === "true"
      );
    } catch {
      return false;
    }
  });

  const lastActivityRef = useRef(Date.now());
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Track user activity to reset idle timer
  useEffect(() => {
    const onActivity = () => {
      lastActivityRef.current = Date.now();
    };
    const events = ["mousemove", "mousedown", "keydown", "touchstart", "scroll"];
    events.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));
    return () => {
      events.forEach((e) => window.removeEventListener(e, onActivity));
    };
  }, []);

  // Idle detection: when idle > 5s and no tasks/schedules, show onboarding
  useEffect(() => {
    if (dismissed || stepIndex !== null) return;
    // Don't trigger if user has active work
    if (hasActiveTasks || hasSchedules) return;

    const check = () => {
      const elapsed = Date.now() - lastActivityRef.current;
      if (elapsed >= ONBOARDING_IDLE_MS) {
        setStepIndex(0);
      } else {
        idleTimerRef.current = setTimeout(check, ONBOARDING_IDLE_MS - elapsed + 100);
      }
    };

    idleTimerRef.current = setTimeout(check, ONBOARDING_IDLE_MS);
    return () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    };
  }, [dismissed, stepIndex, hasActiveTasks, hasSchedules]);

  const nextStep = useCallback(() => {
    setStepIndex((prev) => {
      if (prev === null) return null;
      if (prev >= steps.length - 1) {
        // Completed all steps
        try {
          localStorage.setItem(ONBOARDING_STORAGE_KEY, "true");
        } catch { /* ignore */ }
        return null;
      }
      return prev + 1;
    });
  }, [steps.length]);

  const prevStep = useCallback(() => {
    setStepIndex((prev) => {
      if (prev === null || prev <= 0) return prev;
      return prev - 1;
    });
  }, []);

  const dismiss = useCallback(() => {
    setStepIndex(null);
    setDismissed(true);
    try {
      localStorage.setItem(ONBOARDING_DISMISSED_KEY, "true");
    } catch { /* ignore */ }
  }, []);

  const restart = useCallback(() => {
    setDismissed(false);
    setStepIndex(0);
    try {
      localStorage.removeItem(ONBOARDING_STORAGE_KEY);
      localStorage.removeItem(ONBOARDING_DISMISSED_KEY);
    } catch { /* ignore */ }
  }, []);

  const isActive = stepIndex !== null;
  const currentStep = isActive ? steps[stepIndex] : null;

  return {
    isActive,
    currentStepIndex: stepIndex,
    currentStep,
    nextStep,
    prevStep,
    dismiss,
    restart,
    totalSteps: steps.length,
  };
}
