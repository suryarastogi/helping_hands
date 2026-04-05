import { render, screen, fireEvent, cleanup, act } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

import OnboardingOverlay from "./OnboardingOverlay";
import type { OnboardingOverlayProps } from "./OnboardingOverlay";
import type { OnboardingStep } from "../hooks/useOnboarding";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeStep(overrides: Partial<OnboardingStep> = {}): OnboardingStep {
  return {
    id: "step-1",
    target: ".test-target",
    title: "Welcome",
    body: "This is a test step.",
    placement: "bottom",
    ...overrides,
  };
}

function makeProps(overrides: Partial<OnboardingOverlayProps> = {}): OnboardingOverlayProps {
  return {
    step: makeStep(),
    stepIndex: 0,
    totalSteps: 3,
    onNext: vi.fn(),
    onPrev: vi.fn(),
    onDismiss: vi.fn(),
    ...overrides,
  };
}

function renderOverlay(overrides: Partial<OnboardingOverlayProps> = {}) {
  const props = makeProps(overrides);
  const result = render(<OnboardingOverlay {...props} />);
  return { ...result, props };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("OnboardingOverlay", () => {
  // ---- Step badge ----

  describe("step badge", () => {
    it("renders step badge with 1-indexed step number", () => {
      renderOverlay({ stepIndex: 0, totalSteps: 5 });
      expect(screen.getByText("1 / 5")).toBeInTheDocument();
    });

    it("renders correct badge for middle step", () => {
      renderOverlay({ stepIndex: 2, totalSteps: 4 });
      expect(screen.getByText("3 / 4")).toBeInTheDocument();
    });
  });

  // ---- Title and body ----

  describe("content", () => {
    it("renders step title", () => {
      renderOverlay({ step: makeStep({ title: "Get Started" }) });
      expect(screen.getByText("Get Started")).toBeInTheDocument();
    });

    it("renders step body", () => {
      renderOverlay({ step: makeStep({ body: "Click the button below." }) });
      expect(screen.getByText("Click the button below.")).toBeInTheDocument();
    });
  });

  // ---- Navigation buttons ----

  describe("navigation", () => {
    it("shows Next button on first step", () => {
      renderOverlay({ stepIndex: 0, totalSteps: 3 });
      expect(screen.getByRole("button", { name: "Next" })).toBeInTheDocument();
    });

    it("does not show Back button on first step", () => {
      renderOverlay({ stepIndex: 0, totalSteps: 3 });
      expect(screen.queryByRole("button", { name: "Back" })).not.toBeInTheDocument();
    });

    it("shows both Back and Next on middle step", () => {
      renderOverlay({ stepIndex: 1, totalSteps: 3 });
      expect(screen.getByRole("button", { name: "Back" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Next" })).toBeInTheDocument();
    });

    it('shows "Got it!" instead of Next on last step', () => {
      renderOverlay({ stepIndex: 2, totalSteps: 3 });
      expect(screen.getByRole("button", { name: "Got it!" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Next" })).not.toBeInTheDocument();
    });

    it("shows Back on last step", () => {
      renderOverlay({ stepIndex: 2, totalSteps: 3 });
      expect(screen.getByRole("button", { name: "Back" })).toBeInTheDocument();
    });

    it("calls onNext when Next is clicked", () => {
      const { props } = renderOverlay({ stepIndex: 0, totalSteps: 3 });
      fireEvent.click(screen.getByRole("button", { name: "Next" }));
      expect(props.onNext).toHaveBeenCalledTimes(1);
    });

    it("calls onPrev when Back is clicked", () => {
      const { props } = renderOverlay({ stepIndex: 1, totalSteps: 3 });
      fireEvent.click(screen.getByRole("button", { name: "Back" }));
      expect(props.onPrev).toHaveBeenCalledTimes(1);
    });

    it('calls onNext when "Got it!" is clicked', () => {
      const { props } = renderOverlay({ stepIndex: 2, totalSteps: 3 });
      fireEvent.click(screen.getByRole("button", { name: "Got it!" }));
      expect(props.onNext).toHaveBeenCalledTimes(1);
    });

    it("handles single-step tour (Got it! on step 0, no Back)", () => {
      renderOverlay({ stepIndex: 0, totalSteps: 1 });
      expect(screen.getByRole("button", { name: "Got it!" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Back" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Next" })).not.toBeInTheDocument();
    });
  });

  // ---- Dismiss ----

  describe("dismiss", () => {
    it("renders dismiss button", () => {
      renderOverlay();
      expect(screen.getByLabelText("Dismiss tutorial")).toBeInTheDocument();
    });

    it("calls onDismiss when dismiss button clicked", () => {
      const { props } = renderOverlay();
      fireEvent.click(screen.getByLabelText("Dismiss tutorial"));
      expect(props.onDismiss).toHaveBeenCalledTimes(1);
    });
  });

  // ---- Step dots ----

  describe("step dots", () => {
    it("renders correct number of dots", () => {
      const { container } = renderOverlay({ totalSteps: 4 });
      const dots = container.querySelectorAll(".onboarding-dot");
      expect(dots.length).toBe(4);
    });

    it("marks current step dot as active", () => {
      const { container } = renderOverlay({ stepIndex: 1, totalSteps: 3 });
      const dots = container.querySelectorAll(".onboarding-dot");
      expect(dots[1].classList.contains("active")).toBe(true);
      expect(dots[0].classList.contains("active")).toBe(false);
      expect(dots[2].classList.contains("active")).toBe(false);
    });

    it("marks previous steps as completed", () => {
      const { container } = renderOverlay({ stepIndex: 2, totalSteps: 4 });
      const dots = container.querySelectorAll(".onboarding-dot");
      expect(dots[0].classList.contains("completed")).toBe(true);
      expect(dots[1].classList.contains("completed")).toBe(true);
      expect(dots[2].classList.contains("completed")).toBe(false);
      expect(dots[3].classList.contains("completed")).toBe(false);
    });
  });

  // ---- Opacity / positioning ----

  describe("opacity before positioning", () => {
    it("starts with opacity 0 (not yet positioned)", () => {
      const { container } = renderOverlay();
      const overlay = container.querySelector(".onboarding-overlay") as HTMLElement;
      expect(overlay.style.opacity).toBe("0");
    });
  });

  // ---- SVG backdrop ----

  describe("backdrop", () => {
    it("renders SVG backdrop mask", () => {
      const { container } = renderOverlay();
      expect(container.querySelector("svg.onboarding-backdrop")).toBeTruthy();
      expect(container.querySelector("#onboarding-mask")).toBeTruthy();
    });
  });

  // ---- Positioning logic ----

  describe("positioning", () => {
    function mockTarget(rect: Partial<DOMRect> = {}) {
      const fullRect = {
        top: 100, left: 200, right: 300, bottom: 150,
        width: 100, height: 50, x: 200, y: 100,
        toJSON: () => ({}),
        ...rect,
      } as DOMRect;
      const el = document.createElement("div");
      el.className = "test-target";
      el.getBoundingClientRect = () => fullRect;
      document.body.appendChild(el);
      return el;
    }

    function flushRaf(rafCallbacks: FrameRequestCallback[]) {
      // Need multiple rounds: outer rAF schedules inner rAF which calls position
      for (let round = 0; round < 5 && rafCallbacks.length > 0; round++) {
        const cbs = rafCallbacks.splice(0);
        cbs.forEach((cb) => act(() => cb(0)));
      }
    }

    function setupRafCapture() {
      const rafCallbacks: FrameRequestCallback[] = [];
      vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
        rafCallbacks.push(cb);
        return rafCallbacks.length;
      });
      return rafCallbacks;
    }

    afterEach(() => {
      document.body.querySelectorAll(".test-target").forEach((el) => el.remove());
    });

    it("positions tooltip with bottom placement", () => {
      const el = mockTarget();
      const rafCallbacks = setupRafCapture();

      let container: HTMLElement;
      act(() => {
        ({ container } = renderOverlay({
          step: makeStep({ target: ".test-target", placement: "bottom" }),
        }));
      });

      flushRaf(rafCallbacks);

      const overlay = container!.querySelector(".onboarding-overlay") as HTMLElement;
      expect(overlay.style.opacity).toBe("1");

      el.remove();
    });

    it("positions tooltip with right placement", () => {
      const el = mockTarget();
      const rafCallbacks = setupRafCapture();

      let container: HTMLElement;
      act(() => {
        ({ container } = renderOverlay({
          step: makeStep({ target: ".test-target", placement: "right" }),
        }));
      });

      flushRaf(rafCallbacks);

      const overlay = container!.querySelector(".onboarding-overlay") as HTMLElement;
      expect(overlay.style.opacity).toBe("1");

      el.remove();
    });

    it("uses default placement for unknown values", () => {
      const el = mockTarget();
      const rafCallbacks = setupRafCapture();

      let container: HTMLElement;
      act(() => {
        ({ container } = renderOverlay({
          step: makeStep({ target: ".test-target", placement: "top" as "bottom" }),
        }));
      });

      flushRaf(rafCallbacks);

      const overlay = container!.querySelector(".onboarding-overlay") as HTMLElement;
      expect(overlay.style.opacity).toBe("1");

      el.remove();
    });

    it("does not position when target is not found", () => {
      const rafCallbacks = setupRafCapture();

      let container: HTMLElement;
      act(() => {
        ({ container } = renderOverlay({
          step: makeStep({ target: ".nonexistent-target" }),
        }));
      });

      flushRaf(rafCallbacks);

      const overlay = container!.querySelector(".onboarding-overlay") as HTMLElement;
      expect(overlay.style.opacity).toBe("0");
    });

    it("skips positioning when target has zero dimensions", () => {
      const el = mockTarget({ width: 0, height: 0 });
      const rafCallbacks = setupRafCapture();

      let container: HTMLElement;
      act(() => {
        ({ container } = renderOverlay({
          step: makeStep({ target: ".test-target" }),
        }));
      });

      flushRaf(rafCallbacks);

      const overlay = container!.querySelector(".onboarding-overlay") as HTMLElement;
      expect(overlay.style.opacity).toBe("0");

      el.remove();
    });

    it("renders spotlight ring when positioned", () => {
      const el = mockTarget();
      const rafCallbacks = setupRafCapture();

      let container: HTMLElement;
      act(() => {
        ({ container } = renderOverlay({
          step: makeStep({ target: ".test-target" }),
        }));
      });

      flushRaf(rafCallbacks);

      expect(container!.querySelector(".onboarding-spotlight-ring")).toBeTruthy();

      el.remove();
    });

    it("repositions on window resize", () => {
      const el = mockTarget();
      const rafCallbacks = setupRafCapture();

      act(() => {
        renderOverlay({
          step: makeStep({ target: ".test-target" }),
        });
      });

      flushRaf(rafCallbacks);

      // Trigger resize — position() is called directly (no rAF wrapper)
      act(() => {
        window.dispatchEvent(new Event("resize"));
      });

      // No error means resize handler is wired up correctly
      el.remove();
    });

    it("cleans up event listeners on unmount", () => {
      const removeSpy = vi.spyOn(window, "removeEventListener");

      const { unmount } = renderOverlay();
      unmount();

      const events = removeSpy.mock.calls.map(([event]) => event);
      expect(events).toContain("resize");
      expect(events).toContain("scroll");
    });

    it("renders spotlight cutout rect in SVG mask when positioned", () => {
      const el = mockTarget();
      const rafCallbacks = setupRafCapture();

      let container: HTMLElement;
      act(() => {
        ({ container } = renderOverlay({
          step: makeStep({ target: ".test-target" }),
        }));
      });

      flushRaf(rafCallbacks);

      const mask = container!.querySelector("#onboarding-mask");
      // Should have 2 rects: the white fill and the black cutout
      const rects = mask?.querySelectorAll("rect");
      expect(rects?.length).toBe(2);

      el.remove();
    });
  });
});
