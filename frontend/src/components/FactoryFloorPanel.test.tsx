import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import FactoryFloorPanel from "./FactoryFloorPanel";
import type { FactoryFloorPanelProps } from "./FactoryFloorPanel";
import type { WorldDecoration } from "../types";

const BASE_PROPS: FactoryFloorPanelProps = {
  maxWorkers: 8,
  activeWorkerCount: 0,
  connectionStatus: "connected",
  decorations: [],
  onClearDecorations: vi.fn(),
  decoOnCooldown: false,
  selectedDecoEmoji: null,
  onSelectedDecoEmojiChange: vi.fn(),
};

describe("FactoryFloorPanel component", () => {
  it("renders header and station/active counts", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} maxWorkers={12} activeWorkerCount={3} />);
    const summary = container.querySelector(".zen-status-summary");
    expect(summary).toBeTruthy();
    expect(summary?.textContent).toContain("Factory Floor");
    expect(summary?.textContent).toContain("12 Stations");
    expect(summary?.textContent).toContain("3 Active");
  });

  // --- Connection status ---

  it("shows multiplayer active hint when connected", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} connectionStatus="connected" />);
    expect(container.querySelector(".status-summary-hint")?.textContent).toContain("Multiplayer active");
  });

  it("shows disconnected hint", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} connectionStatus="disconnected" />);
    expect(container.querySelector(".status-summary-hint")?.textContent).toContain("Disconnected");
  });

  it("shows connecting hint", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} connectionStatus="connecting" />);
    expect(container.querySelector(".status-summary-hint")?.textContent).toContain("Connecting");
  });

  it("shows connection failed hint", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} connectionStatus="failed" />);
    expect(container.querySelector(".status-summary-hint")?.textContent).toContain("Connection failed");
  });

  // --- Decorations ---

  it("renders decoration toolbar when connected", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} connectionStatus="connected" />);
    expect(container.querySelector(".decoration-toolbar")).toBeTruthy();
  });

  it("hides decoration toolbar when disconnected", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} connectionStatus="disconnected" />);
    expect(container.querySelector(".decoration-toolbar")).toBeNull();
  });

  it("renders 8 decoration emoji buttons", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} />);
    expect(container.querySelectorAll(".decoration-emoji-btn")).toHaveLength(8);
  });

  it("shows decoration count", () => {
    const decos: WorldDecoration[] = [
      { id: "d1", emoji: "\u{1F338}", x: 30, y: 40, placedBy: "Alice", color: "#e11d48", placedAt: 1000 },
    ];
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} decorations={decos} />);
    expect(container.querySelector(".decoration-toolbar-header")?.textContent).toContain("1/20");
  });

  it("calls onSelectedDecoEmojiChange when emoji button clicked", () => {
    const onChange = vi.fn();
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} onSelectedDecoEmojiChange={onChange} />);
    fireEvent.click(container.querySelectorAll(".decoration-emoji-btn")[0]);
    expect(onChange).toHaveBeenCalled();
  });

  it("shows clear button when decorations exist", () => {
    const decos: WorldDecoration[] = [
      { id: "d1", emoji: "\u{1F338}", x: 30, y: 40, placedBy: "Alice", color: "#e11d48", placedAt: 1000 },
    ];
    const onClear = vi.fn();
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} decorations={decos} onClearDecorations={onClear} />);
    const btn = container.querySelector(".decoration-clear-btn");
    expect(btn).toBeTruthy();
    fireEvent.click(btn!);
    expect(onClear).toHaveBeenCalled();
  });

  it("hides clear button when no decorations", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} decorations={[]} />);
    expect(container.querySelector(".decoration-clear-btn")).toBeNull();
  });

  it("shows placement hint when deco emoji is selected", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} selectedDecoEmoji="\u{1F338}" />);
    expect(container.querySelector(".decoration-hint")?.textContent).toContain("Double-click");
  });

  it("hides placement hint when no deco emoji selected", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} selectedDecoEmoji={null} />);
    expect(container.querySelector(".decoration-hint")).toBeNull();
  });

  it("disables decoration emoji buttons during cooldown", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} decoOnCooldown={true} />);
    const buttons = container.querySelectorAll(".decoration-emoji-btn");
    expect(buttons.length).toBeGreaterThan(0);
    buttons.forEach((btn) => {
      expect((btn as HTMLButtonElement).disabled).toBe(true);
    });
  });

  it("enables decoration emoji buttons when not on cooldown", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} decoOnCooldown={false} />);
    const buttons = container.querySelectorAll(".decoration-emoji-btn");
    expect(buttons.length).toBeGreaterThan(0);
    buttons.forEach((btn) => {
      expect((btn as HTMLButtonElement).disabled).toBe(false);
    });
  });
});
