import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";

import {
  useOnboarding,
  buildOnboardingSteps,
  ONBOARDING_IDLE_MS,
} from "./useOnboarding";

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.useFakeTimers();
  localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// buildOnboardingSteps
// ---------------------------------------------------------------------------

describe("buildOnboardingSteps", () => {
  it("returns BASE_STEPS when server has GitHub token", () => {
    const steps = buildOnboardingSteps(true);
    expect(steps.every((s) => s.id !== "github-token")).toBe(true);
    expect(steps.length).toBe(5);
  });

  it("injects github-token step when server lacks token", () => {
    const steps = buildOnboardingSteps(false);
    expect(steps.some((s) => s.id === "github-token")).toBe(true);
    expect(steps.length).toBe(6);
  });

  it("places github-token step before submit-btn", () => {
    const steps = buildOnboardingSteps(false);
    const tokenIdx = steps.findIndex((s) => s.id === "github-token");
    const submitIdx = steps.findIndex((s) => s.id === "submit-btn");
    expect(tokenIdx).toBeLessThan(submitIdx);
  });

  it("every step has required fields", () => {
    for (const hasToken of [true, false]) {
      const steps = buildOnboardingSteps(hasToken);
      for (const step of steps) {
        expect(step.id).toBeTruthy();
        expect(step.target).toBeTruthy();
        expect(step.title).toBeTruthy();
        expect(step.body).toBeTruthy();
        expect(["right", "bottom"]).toContain(step.placement);
      }
    }
  });
});

// ---------------------------------------------------------------------------
// useOnboarding — idle detection
// ---------------------------------------------------------------------------

describe("useOnboarding — idle detection", () => {
  it("starts inactive", () => {
    const { result } = renderHook(() =>
      useOnboarding({ hasActiveTasks: false, hasSchedules: false, serverHasGithubToken: true }),
    );
    expect(result.current.isActive).toBe(false);
    expect(result.current.currentStepIndex).toBeNull();
    expect(result.current.currentStep).toBeNull();
  });

  it("activates after idle timeout", () => {
    const { result } = renderHook(() =>
      useOnboarding({ hasActiveTasks: false, hasSchedules: false, serverHasGithubToken: true }),
    );
    act(() => {
      vi.advanceTimersByTime(ONBOARDING_IDLE_MS + 200);
    });
    expect(result.current.isActive).toBe(true);
    expect(result.current.currentStepIndex).toBe(0);
    expect(result.current.currentStep).not.toBeNull();
  });

  it("does not activate when user has active tasks", () => {
    const { result } = renderHook(() =>
      useOnboarding({ hasActiveTasks: true, hasSchedules: false, serverHasGithubToken: true }),
    );
    act(() => {
      vi.advanceTimersByTime(ONBOARDING_IDLE_MS + 200);
    });
    expect(result.current.isActive).toBe(false);
  });

  it("does not activate when user has schedules", () => {
    const { result } = renderHook(() =>
      useOnboarding({ hasActiveTasks: false, hasSchedules: true, serverHasGithubToken: true }),
    );
    act(() => {
      vi.advanceTimersByTime(ONBOARDING_IDLE_MS + 200);
    });
    expect(result.current.isActive).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// useOnboarding — step navigation
// ---------------------------------------------------------------------------

describe("useOnboarding — step navigation", () => {
  function activateOnboarding() {
    const hook = renderHook(() =>
      useOnboarding({ hasActiveTasks: false, hasSchedules: false, serverHasGithubToken: true }),
    );
    act(() => {
      vi.advanceTimersByTime(ONBOARDING_IDLE_MS + 200);
    });
    return hook;
  }

  it("advances to next step", () => {
    const { result } = activateOnboarding();
    expect(result.current.currentStepIndex).toBe(0);

    act(() => result.current.nextStep());
    expect(result.current.currentStepIndex).toBe(1);
  });

  it("goes back to previous step", () => {
    const { result } = activateOnboarding();
    act(() => result.current.nextStep());
    expect(result.current.currentStepIndex).toBe(1);

    act(() => result.current.prevStep());
    expect(result.current.currentStepIndex).toBe(0);
  });

  it("prevStep does nothing at step 0", () => {
    const { result } = activateOnboarding();
    act(() => result.current.prevStep());
    expect(result.current.currentStepIndex).toBe(0);
  });

  it("completing last step deactivates and marks completed", () => {
    const { result } = activateOnboarding();
    const totalSteps = result.current.totalSteps;

    for (let i = 0; i < totalSteps; i++) {
      act(() => result.current.nextStep());
    }

    expect(result.current.isActive).toBe(false);
    expect(result.current.currentStepIndex).toBeNull();
    expect(localStorage.getItem("hh_onboarding_completed")).toBe("true");
  });

  it("reports correct totalSteps", () => {
    const { result } = activateOnboarding();
    expect(result.current.totalSteps).toBe(5);
  });
});

// ---------------------------------------------------------------------------
// useOnboarding — dismiss & restart
// ---------------------------------------------------------------------------

describe("useOnboarding — dismiss & restart", () => {
  it("dismiss deactivates and persists", () => {
    const { result } = renderHook(() =>
      useOnboarding({ hasActiveTasks: false, hasSchedules: false, serverHasGithubToken: true }),
    );
    act(() => {
      vi.advanceTimersByTime(ONBOARDING_IDLE_MS + 200);
    });
    expect(result.current.isActive).toBe(true);

    act(() => result.current.dismiss());
    expect(result.current.isActive).toBe(false);
    expect(localStorage.getItem("hh_onboarding_dismissed")).toBe("true");
  });

  it("does not reactivate after dismiss even with idle", () => {
    const { result } = renderHook(() =>
      useOnboarding({ hasActiveTasks: false, hasSchedules: false, serverHasGithubToken: true }),
    );
    act(() => {
      vi.advanceTimersByTime(ONBOARDING_IDLE_MS + 200);
    });
    act(() => result.current.dismiss());

    act(() => {
      vi.advanceTimersByTime(ONBOARDING_IDLE_MS * 2);
    });
    expect(result.current.isActive).toBe(false);
  });

  it("restart clears dismissed state and starts at step 0", () => {
    const { result } = renderHook(() =>
      useOnboarding({ hasActiveTasks: false, hasSchedules: false, serverHasGithubToken: true }),
    );
    act(() => {
      vi.advanceTimersByTime(ONBOARDING_IDLE_MS + 200);
    });
    act(() => result.current.dismiss());
    expect(result.current.isActive).toBe(false);

    act(() => result.current.restart());
    expect(result.current.isActive).toBe(true);
    expect(result.current.currentStepIndex).toBe(0);
    expect(localStorage.getItem("hh_onboarding_dismissed")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// useOnboarding — localStorage persistence
// ---------------------------------------------------------------------------

describe("useOnboarding — localStorage", () => {
  it("does not activate when previously completed", () => {
    localStorage.setItem("hh_onboarding_completed", "true");

    const { result } = renderHook(() =>
      useOnboarding({ hasActiveTasks: false, hasSchedules: false, serverHasGithubToken: true }),
    );
    act(() => {
      vi.advanceTimersByTime(ONBOARDING_IDLE_MS + 200);
    });
    expect(result.current.isActive).toBe(false);
  });

  it("does not activate when previously dismissed", () => {
    localStorage.setItem("hh_onboarding_dismissed", "true");

    const { result } = renderHook(() =>
      useOnboarding({ hasActiveTasks: false, hasSchedules: false, serverHasGithubToken: true }),
    );
    act(() => {
      vi.advanceTimersByTime(ONBOARDING_IDLE_MS + 200);
    });
    expect(result.current.isActive).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// useOnboarding — GitHub token step
// ---------------------------------------------------------------------------

describe("useOnboarding — GitHub token step", () => {
  it("includes extra step when server lacks token", () => {
    const { result } = renderHook(() =>
      useOnboarding({ hasActiveTasks: false, hasSchedules: false, serverHasGithubToken: false }),
    );
    expect(result.current.totalSteps).toBe(6);
  });

  it("omits extra step when server has token", () => {
    const { result } = renderHook(() =>
      useOnboarding({ hasActiveTasks: false, hasSchedules: false, serverHasGithubToken: true }),
    );
    expect(result.current.totalSteps).toBe(5);
  });
});
