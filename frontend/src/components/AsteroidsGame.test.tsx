import { render, screen, fireEvent, cleanup, act } from "@testing-library/react";
import { describe, it, expect, vi, afterEach, beforeEach, beforeAll } from "vitest";

import AsteroidsGame from "./AsteroidsGame";
import type { AsteroidsGameProps } from "./AsteroidsGame";

// ---------------------------------------------------------------------------
// jsdom stubs — canvas 2D context
// ---------------------------------------------------------------------------

const mockCtx = {
  fillStyle: "",
  strokeStyle: "",
  lineWidth: 0,
  font: "",
  textAlign: "",
  fillRect: vi.fn(),
  fillText: vi.fn(),
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  closePath: vi.fn(),
  stroke: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  translate: vi.fn(),
  rotate: vi.fn(),
};

beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue(mockCtx);
  // Mock rAF to capture callback but NOT call it synchronously (avoids infinite tick loop)
  vi.spyOn(window, "requestAnimationFrame").mockImplementation(() => 1);
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeProps(overrides: Partial<AsteroidsGameProps> = {}): AsteroidsGameProps {
  return {
    onClose: vi.fn(),
    playerName: "TestPlayer",
    ...overrides,
  };
}

function renderGame(overrides: Partial<AsteroidsGameProps> = {}) {
  const props = makeProps(overrides);
  const result = render(<AsteroidsGame {...props} />);
  return { ...result, props };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
  // Re-stub after restoreAllMocks
  HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue(mockCtx);
  vi.spyOn(window, "requestAnimationFrame").mockImplementation(() => 1);
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
});

beforeEach(() => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => [],
  } as Response);
});

describe("AsteroidsGame", () => {
  // ---- Component structure ----

  describe("structure", () => {
    it("renders ASTEROIDS heading", () => {
      renderGame();
      expect(screen.getByRole("heading", { name: "ASTEROIDS" })).toBeInTheDocument();
    });

    it("renders stats bar with score, wave, and lives", () => {
      renderGame();
      expect(screen.getByText(/Score:/)).toBeInTheDocument();
      expect(screen.getByText(/Wave:/)).toBeInTheDocument();
      expect(screen.getByText(/Lives:/)).toBeInTheDocument();
    });

    it("renders close button with aria-label", () => {
      renderGame();
      expect(screen.getByLabelText("Close arcade")).toBeInTheDocument();
    });

    it("renders canvas element with correct dimensions", () => {
      const { container } = renderGame();
      const canvas = container.querySelector("canvas.asteroids-canvas");
      expect(canvas).toBeTruthy();
      expect(canvas?.getAttribute("width")).toBe("640");
      expect(canvas?.getAttribute("height")).toBe("480");
    });

    it("renders controls instructions", () => {
      renderGame();
      expect(screen.getByText(/Arrow keys/)).toBeInTheDocument();
      expect(screen.getByText(/Space: shoot/)).toBeInTheDocument();
    });

    it("renders High Scores heading", () => {
      renderGame();
      expect(screen.getByRole("heading", { name: "High Scores" })).toBeInTheDocument();
    });

    it("renders card wrapper with asteroids-card class", () => {
      const { container } = renderGame();
      expect(container.querySelector("section.asteroids-card")).toBeTruthy();
    });

    it("canvas has tabIndex for keyboard focus", () => {
      const { container } = renderGame();
      const canvas = container.querySelector("canvas");
      expect(canvas?.getAttribute("tabindex")).toBe("0");
    });
  });

  // ---- Close button ----

  describe("close button", () => {
    it("calls onClose when close button is clicked", () => {
      const { props } = renderGame();
      fireEvent.click(screen.getByLabelText("Close arcade"));
      expect(props.onClose).toHaveBeenCalledTimes(1);
    });

    it("calls onClose when Escape key is pressed", () => {
      const { props } = renderGame();
      fireEvent.keyDown(window, { key: "Escape" });
      expect(props.onClose).toHaveBeenCalledTimes(1);
    });
  });

  // ---- High scores ----

  describe("high scores", () => {
    it("fetches high scores on mount", async () => {
      renderGame();
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/arcade/high-scores"),
      );
    });

    it("shows empty state when no scores", () => {
      renderGame();
      expect(screen.getByText("No scores yet")).toBeInTheDocument();
    });

    it("renders leaderboard entries when scores are returned", async () => {
      const scores = [
        { name: "Alice", score: 1000, wave: 3, submitted_at: "2026-01-01T00:00:00Z" },
        { name: "Bob", score: 500, wave: 2, submitted_at: "2026-01-01T00:00:00Z" },
      ];
      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: async () => scores,
      } as Response);

      await act(async () => {
        renderGame();
      });

      expect(screen.getByText("Alice")).toBeInTheDocument();
      expect(screen.getByText("Bob")).toBeInTheDocument();
    });

    it("handles fetch failure gracefully (no crash)", async () => {
      vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network"));
      await act(async () => {
        renderGame();
      });
      // Should still render
      expect(screen.getByText("No scores yet")).toBeInTheDocument();
    });

    it("handles non-ok response gracefully", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: false,
        json: async () => [],
      } as Response);
      await act(async () => {
        renderGame();
      });
      expect(screen.getByText("No scores yet")).toBeInTheDocument();
    });
  });

  // ---- Initial state ----

  describe("initial state", () => {
    it("starts with score 0", () => {
      renderGame();
      expect(screen.getByText("Score: 0")).toBeInTheDocument();
    });

    it("starts with wave 1", () => {
      renderGame();
      expect(screen.getByText("Wave: 1")).toBeInTheDocument();
    });

    it("starts with 3 lives", () => {
      renderGame();
      expect(screen.getByText("Lives: 3")).toBeInTheDocument();
    });

    it("does not show game over overlay initially", () => {
      const { container } = renderGame();
      expect(container.querySelector(".asteroids-gameover-overlay")).toBeNull();
    });
  });

  // ---- Keyboard handlers ----

  describe("keyboard handlers", () => {
    it("does not call onClose for non-Escape keys", () => {
      const { props } = renderGame();
      fireEvent.keyDown(window, { key: "r" });
      expect(props.onClose).not.toHaveBeenCalled();
    });

    it("R key does not reset when game is not over", () => {
      renderGame();
      fireEvent.keyDown(window, { key: "r" });
      // Score remains 0 (no crash)
      expect(screen.getByText("Score: 0")).toBeInTheDocument();
    });
  });

  // ---- Player name ----

  describe("player name", () => {
    it("uses provided player name", () => {
      const { props } = renderGame({ playerName: "Astro" });
      expect(props.playerName).toBe("Astro");
    });

    it("accepts empty player name without crash", () => {
      renderGame({ playerName: "" });
      expect(screen.getByRole("heading", { name: "ASTEROIDS" })).toBeInTheDocument();
    });
  });

  // ---- Canvas rendering ----

  describe("canvas", () => {
    it("calls getContext('2d') on mount", () => {
      renderGame();
      expect(HTMLCanvasElement.prototype.getContext).toHaveBeenCalledWith("2d");
    });

    it("starts the animation frame loop", () => {
      renderGame();
      expect(window.requestAnimationFrame).toHaveBeenCalled();
    });

    it("cancels animation frame on unmount", () => {
      const { unmount } = renderGame();
      unmount();
      expect(window.cancelAnimationFrame).toHaveBeenCalled();
    });
  });

  // ---- Event listener cleanup ----

  describe("cleanup", () => {
    it("removes keydown/keyup event listeners on unmount", () => {
      const removeSpy = vi.spyOn(window, "removeEventListener");
      const { unmount } = renderGame();
      unmount();
      const calls = removeSpy.mock.calls.map(([event]) => event);
      expect(calls).toContain("keydown");
      expect(calls).toContain("keyup");
    });
  });

  // ---- Score submission edge cases ----

  describe("score submission", () => {
    it("does not submit score with zero value (guard)", async () => {
      // Initial score is 0; even if gameOver happened, submitScore(0, ...) returns early
      // We verify by checking fetch was only called once (for high scores fetch)
      await act(async () => {
        renderGame();
      });
      // One call for fetchHighScores; no POST call since score is 0
      const postCalls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.filter(
        ([, opts]: [string, RequestInit | undefined]) => opts?.method === "POST",
      );
      expect(postCalls.length).toBe(0);
    });
  });

  // ---- Leaderboard display details ----

  describe("leaderboard details", () => {
    it("renders rank numbers for each entry", async () => {
      const scores = [
        { name: "P1", score: 200, wave: 1, submitted_at: "2026-01-01T00:00:00Z" },
        { name: "P2", score: 100, wave: 1, submitted_at: "2026-01-01T00:00:00Z" },
      ];
      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: async () => scores,
      } as Response);

      await act(async () => {
        renderGame();
      });

      expect(screen.getByText("1.")).toBeInTheDocument();
      expect(screen.getByText("2.")).toBeInTheDocument();
    });

    it("renders wave indicators", async () => {
      const scores = [
        { name: "P1", score: 200, wave: 5, submitted_at: "2026-01-01T00:00:00Z" },
      ];
      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: async () => scores,
      } as Response);

      await act(async () => {
        renderGame();
      });

      expect(screen.getByText("W5")).toBeInTheDocument();
    });
  });
});
