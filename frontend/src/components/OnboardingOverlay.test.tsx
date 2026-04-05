import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";

afterEach(cleanup);

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
});
