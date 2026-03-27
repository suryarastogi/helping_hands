import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import Minimap from "./Minimap";

describe("Minimap", () => {
  const defaultProps = {
    playerPosition: { x: 50, y: 50 },
    remotePlayers: [],
    workers: [],
  };

  it("renders with aria-label", () => {
    const { container } = render(<Minimap {...defaultProps} />);
    expect(container.querySelector("[aria-label='Minimap']")).toBeTruthy();
  });

  it("renders the local player dot", () => {
    const { container } = render(<Minimap {...defaultProps} />);
    const dot = container.querySelector(".minimap-dot-local") as HTMLElement;
    expect(dot).toBeTruthy();
    expect(dot.getAttribute("aria-label")).toBe("You");
    expect(dot.style.left).toBe("50%");
    expect(dot.style.top).toBe("50%");
  });

  it("renders remote player dots with colours", () => {
    const remotePlayers = [
      {
        player_id: "1",
        name: "Alice",
        color: "#e11d48",
        x: 30,
        y: 40,
        direction: "left" as const,
        walking: false,
        idle: false,
        typing: false,
      },
      {
        player_id: "2",
        name: "Bob",
        color: "#2563eb",
        x: 70,
        y: 60,
        direction: "right" as const,
        walking: true,
        idle: false,
        typing: false,
      },
    ];
    const { container } = render(<Minimap {...defaultProps} remotePlayers={remotePlayers} />);

    const dots = container.querySelectorAll(".minimap-dot-remote");
    expect(dots).toHaveLength(2);

    const alice = dots[0] as HTMLElement;
    expect(alice.getAttribute("aria-label")).toBe("Alice");
    expect(alice.style.backgroundColor).toBe("rgb(225, 29, 72)");
    expect(alice.style.left).toBe("30%");

    const bob = dots[1] as HTMLElement;
    expect(bob.getAttribute("aria-label")).toBe("Bob");
    expect(bob.style.left).toBe("70%");
  });

  it("renders worker dots", () => {
    const workers = [
      { taskId: "t1", x: 20, y: 30 },
      { taskId: "t2", x: 60, y: 70 },
    ];
    const { container } = render(<Minimap {...defaultProps} workers={workers} />);

    const workerDots = container.querySelectorAll(".minimap-dot-worker");
    expect(workerDots).toHaveLength(2);
    expect((workerDots[0] as HTMLElement).style.left).toBe("20%");
    expect((workerDots[1] as HTMLElement).style.left).toBe("60%");
  });

  it("renders empty when no remote players or workers", () => {
    const { container } = render(<Minimap {...defaultProps} />);
    expect(container.querySelectorAll(".minimap-dot-worker")).toHaveLength(0);
    expect(container.querySelectorAll(".minimap-dot-remote")).toHaveLength(0);
    expect(container.querySelector(".minimap-dot-local")).toBeTruthy();
  });

  it("positions local player dot at provided coordinates", () => {
    const { container } = render(
      <Minimap
        playerPosition={{ x: 10, y: 90 }}
        remotePlayers={[]}
        workers={[]}
      />,
    );
    const dot = container.querySelector(".minimap-dot-local") as HTMLElement;
    expect(dot.style.left).toBe("10%");
    expect(dot.style.top).toBe("90%");
  });

  it("calls onTeleport with click position when provided", () => {
    const onTeleport = vi.fn();
    const { container } = render(
      <Minimap {...defaultProps} onTeleport={onTeleport} />,
    );

    const minimap = container.querySelector(".minimap") as HTMLElement;
    // Mock getBoundingClientRect
    vi.spyOn(minimap, "getBoundingClientRect").mockReturnValue({
      left: 0,
      top: 0,
      width: 120,
      height: 80,
      right: 120,
      bottom: 80,
      x: 0,
      y: 0,
      toJSON: () => {},
    });

    fireEvent.click(minimap, { clientX: 60, clientY: 40 });

    expect(onTeleport).toHaveBeenCalledTimes(1);
    expect(onTeleport).toHaveBeenCalledWith({ x: 50, y: 50 });
  });

  it("adds minimap-clickable class when onTeleport is provided", () => {
    const onTeleport = vi.fn();
    const { container } = render(
      <Minimap {...defaultProps} onTeleport={onTeleport} />,
    );

    const minimap = container.querySelector(".minimap") as HTMLElement;
    expect(minimap.classList.contains("minimap-clickable")).toBe(true);
  });

  it("does not add minimap-clickable class without onTeleport", () => {
    const { container } = render(<Minimap {...defaultProps} />);

    const minimap = container.querySelector(".minimap") as HTMLElement;
    expect(minimap.classList.contains("minimap-clickable")).toBe(false);
  });

  it("does not fire onTeleport when prop is not provided", () => {
    const { container } = render(<Minimap {...defaultProps} />);

    const minimap = container.querySelector(".minimap") as HTMLElement;
    // Should not throw
    fireEvent.click(minimap, { clientX: 60, clientY: 40 });
  });
});
