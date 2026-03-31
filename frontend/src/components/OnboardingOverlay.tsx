import { useEffect, useRef, useState } from "react";

import type { OnboardingStep } from "../hooks/useOnboarding";

export interface OnboardingOverlayProps {
  step: OnboardingStep;
  stepIndex: number;
  totalSteps: number;
  onNext: () => void;
  onPrev: () => void;
  onDismiss: () => void;
}

type TooltipPos = {
  top: number;
  left: number;
  spotlightRect: DOMRect | null;
};

/**
 * Renders a spotlight + tooltip overlay that highlights a target element and
 * displays contextual guidance for the current onboarding step.
 */
export default function OnboardingOverlay({
  step,
  stepIndex,
  totalSteps,
  onNext,
  onPrev,
  onDismiss,
}: OnboardingOverlayProps) {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<TooltipPos>({ top: 0, left: 0, spotlightRect: null });

  // Position the tooltip relative to the target element
  // Hide tooltip until first valid position is computed to avoid the
  // visible jump when the submission overlay is still mounting.
  const [positioned, setPositioned] = useState(false);

  useEffect(() => {
    setPositioned(false);

    const position = () => {
      const target = document.querySelector(step.target);
      if (!target) return; // wait for target to appear

      const rect = target.getBoundingClientRect();
      // Guard against elements that haven't laid out yet (0×0)
      if (rect.width === 0 && rect.height === 0) return;

      const tooltip = tooltipRef.current;
      const tw = tooltip?.offsetWidth ?? 300;
      const th = tooltip?.offsetHeight ?? 160;
      const pad = 14;

      let top = 0;
      let left = 0;

      switch (step.placement) {
        case "right":
          top = rect.top + rect.height / 2 - th / 2;
          left = rect.right + pad;
          break;
        case "bottom":
          top = rect.bottom + pad;
          left = rect.left + rect.width / 2 - tw / 2;
          break;
        default:
          top = rect.bottom + pad;
          left = rect.left;
      }

      // Clamp to viewport
      top = Math.max(8, Math.min(top, window.innerHeight - th - 8));
      left = Math.max(8, Math.min(left, window.innerWidth - tw - 8));

      setPos({ top, left, spotlightRect: rect });
      setPositioned(true);
    };

    // Debounce helper for MutationObserver (fires very frequently)
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;
    const debouncedPosition = () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => requestAnimationFrame(position), 30);
    };

    // Wait two frames for overlay to mount + lay out before first position
    requestAnimationFrame(() => requestAnimationFrame(position));

    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, true);

    const observer = new MutationObserver(debouncedPosition);
    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      window.removeEventListener("resize", position);
      window.removeEventListener("scroll", position, true);
      observer.disconnect();
      if (debounceTimer) clearTimeout(debounceTimer);
    };
  }, [step]);

  const { spotlightRect } = pos;

  return (
    <div className="onboarding-overlay" style={{ opacity: positioned ? 1 : 0 }}>
      {/* Semi-transparent backdrop with a "spotlight" cutout */}
      <svg className="onboarding-backdrop" width="100%" height="100%">
        <defs>
          <mask id="onboarding-mask">
            <rect width="100%" height="100%" fill="white" />
            {spotlightRect && (
              <rect
                x={spotlightRect.left - 6}
                y={spotlightRect.top - 6}
                width={spotlightRect.width + 12}
                height={spotlightRect.height + 12}
                rx="8"
                fill="black"
              />
            )}
          </mask>
        </defs>
        <rect
          width="100%"
          height="100%"
          fill="rgba(2, 8, 23, 0.7)"
          mask="url(#onboarding-mask)"
        />
      </svg>

      {/* Glow ring around the target */}
      {spotlightRect && (
        <div
          className="onboarding-spotlight-ring"
          style={{
            top: spotlightRect.top - 6,
            left: spotlightRect.left - 6,
            width: spotlightRect.width + 12,
            height: spotlightRect.height + 12,
          }}
        />
      )}

      {/* Tooltip card */}
      <div
        ref={tooltipRef}
        className="onboarding-tooltip"
        style={{ top: pos.top, left: pos.left }}
      >
        <div className="onboarding-tooltip-header">
          <span className="onboarding-step-badge">
            {stepIndex + 1} / {totalSteps}
          </span>
          <button
            type="button"
            className="onboarding-dismiss"
            onClick={onDismiss}
            aria-label="Dismiss tutorial"
          >
            &times;
          </button>
        </div>
        <h3 className="onboarding-tooltip-title">{step.title}</h3>
        <p className="onboarding-tooltip-body">{step.body}</p>
        <div className="onboarding-tooltip-actions">
          {stepIndex > 0 && (
            <button type="button" className="onboarding-btn onboarding-btn--secondary" onClick={onPrev}>
              Back
            </button>
          )}
          <button type="button" className="onboarding-btn onboarding-btn--primary" onClick={onNext}>
            {stepIndex < totalSteps - 1 ? "Next" : "Got it!"}
          </button>
        </div>
        {/* Step dots */}
        <div className="onboarding-dots">
          {Array.from({ length: totalSteps }, (_, i) => (
            <span
              key={i}
              className={`onboarding-dot${i === stepIndex ? " active" : ""}${i < stepIndex ? " completed" : ""}`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
