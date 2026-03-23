import { render, within, fireEvent } from "@testing-library/react";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";

import MonitorCard from "./MonitorCard";
import type { MonitorCardProps } from "./MonitorCard";

/** Helper that builds default props for MonitorCard. */
function makeProps(overrides: Partial<MonitorCardProps> = {}): MonitorCardProps {
  return {
    taskId: null,
    status: "idle",
    isPolling: false,
    outputTab: "updates",
    onOutputTabChange: vi.fn(),
    prefixFilters: {},
    onPrefixFiltersChange: vi.fn(),
    activeOutputText: "",
    detectedPrefixes: [],
    accUsage: null,
    taskInputs: [],
    runtimeDisplay: null,
    monitorOutputRef: createRef<HTMLPreElement>(),
    monitorHeight: null,
    onMonitorScroll: vi.fn(),
    onResizeStart: vi.fn(),
    ...overrides,
  };
}

/** Render MonitorCard and return a scoped query helper. */
function renderCard(overrides: Partial<MonitorCardProps> = {}) {
  const props = makeProps(overrides);
  const result = render(<MonitorCard {...props} />);
  const card = within(result.container.querySelector("section")!);
  return { ...result, card, props };
}

describe("MonitorCard", () => {
  it("renders with default idle state", () => {
    const { card } = renderCard();
    expect(card.getByText("Output")).toBeTruthy();
  });

  it("shows task id in title when set", () => {
    const { card } = renderCard({ taskId: "abc-123-def-456" });
    expect(card.getByText(/Output.*abc-123/)).toBeTruthy();
  });

  it("renders three output tabs", () => {
    const { card } = renderCard();
    expect(card.getByRole("tab", { name: "Updates" })).toBeTruthy();
    expect(card.getByRole("tab", { name: "Raw" })).toBeTruthy();
    expect(card.getByRole("tab", { name: "Payload" })).toBeTruthy();
  });

  it("marks the active tab as selected", () => {
    const { card } = renderCard({ outputTab: "raw" });
    expect(card.getByRole("tab", { name: "Raw" }).getAttribute("aria-selected")).toBe("true");
    expect(card.getByRole("tab", { name: "Updates" }).getAttribute("aria-selected")).toBe("false");
  });

  it("calls onOutputTabChange when a tab is clicked", () => {
    const handler = vi.fn();
    const { card } = renderCard({ onOutputTabChange: handler });
    fireEvent.click(card.getByRole("tab", { name: "Payload" }));
    expect(handler).toHaveBeenCalledWith("payload");
  });

  it("shows cancel button for running tasks", () => {
    const { card } = renderCard({ taskId: "task-1", status: "STARTED" });
    expect(card.getByTitle("Cancel this task")).toBeTruthy();
  });

  it("hides cancel button for terminal status", () => {
    const { card } = renderCard({ taskId: "task-1", status: "SUCCESS" });
    expect(card.queryByTitle("Cancel this task")).toBeNull();
  });

  it("renders output text in pre element", () => {
    const { container } = renderCard({ activeOutputText: "hello world" });
    const pre = container.querySelector("pre.monitor-output");
    expect(pre?.textContent).toBe("hello world");
  });

  it("shows runtime display when present", () => {
    const { card } = renderCard({ runtimeDisplay: "2m 30s" });
    expect(card.getByTitle("Elapsed runtime").textContent).toBe("2m 30s");
  });

  it("hides runtime display when null", () => {
    const { card } = renderCard({ runtimeDisplay: null });
    expect(card.queryByTitle("Elapsed runtime")).toBeNull();
  });

  it("renders prefix filter chips when prefixes detected", () => {
    const { card } = renderCard({
      detectedPrefixes: ["INFO", "WARN"],
      outputTab: "updates",
    });
    expect(card.getByText("[INFO]")).toBeTruthy();
    expect(card.getByText("[WARN]")).toBeTruthy();
  });

  it("hides prefix filters when on payload tab", () => {
    const { card } = renderCard({
      detectedPrefixes: ["INFO"],
      outputTab: "payload",
    });
    expect(card.queryByText("[INFO]")).toBeNull();
  });

  it("renders accumulated usage when present", () => {
    const { card } = renderCard({
      accUsage: {
        totalCost: 0.0123,
        totalSeconds: 45,
        totalIn: 1000,
        totalOut: 500,
        count: 3,
      },
    });
    expect(card.getByText(/\$0\.0123/)).toBeTruthy();
  });

  it("renders task inputs when provided", () => {
    const { card } = renderCard({
      taskInputs: [
        { label: "Repo", value: "owner/repo" },
        { label: "Model", value: "gpt-4" },
      ],
    });
    expect(card.getByText("Repo")).toBeTruthy();
    expect(card.getByText("owner/repo")).toBeTruthy();
  });

  it("shows empty message when no task inputs", () => {
    const { card } = renderCard({ taskInputs: [] });
    expect(card.getByText("Inputs not available yet.")).toBeTruthy();
  });

  it("shows pulsing blinker for running status", () => {
    const { card } = renderCard({ status: "STARTED", isPolling: true });
    const blinker = card.getByTitle("STARTED (polling)");
    expect(blinker.className).toContain("pulse");
  });

  it("shows static blinker for idle status", () => {
    const { card } = renderCard({ status: "idle" });
    const blinker = card.getByTitle("idle");
    expect(blinker.className).not.toContain("pulse");
  });

  it("applies custom height to monitor output", () => {
    const { container } = renderCard({ monitorHeight: 200 });
    const pre = container.querySelector("pre.monitor-output") as HTMLElement;
    expect(pre.style.height).toBe("200px");
  });

  it("shows reset button when filters are active", () => {
    const { card } = renderCard({
      detectedPrefixes: ["INFO"],
      prefixFilters: { INFO: "hide" },
      outputTab: "updates",
    });
    expect(card.getByText("Reset")).toBeTruthy();
  });
});
