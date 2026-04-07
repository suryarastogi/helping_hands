import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import WorkerSprite from "./WorkerSprite";
import { TORII_POS } from "../constants";

const BOT_STYLE = {
  bodyColor: "#10a37f",
  accentColor: "#c7fff1",
  skinColor: "#d9f6ef",
  outlineColor: "#0b3e32",
  variant: "bot-alpha" as const,
};

const GOOSE_STYLE = {
  bodyColor: "#ffffff",
  accentColor: "#f97316",
  skinColor: "#e2e8f0",
  outlineColor: "#334155",
  variant: "goose" as const,
};

const BASE_WORKER_PROPS = {
  taskId: "abc-123",
  phase: "active" as const,
  style: BOT_STYLE,
  spriteVariant: "bot-alpha" as const,
  isActive: true,
  isSelected: false,
  provider: "openai",
  plotLeft: 40,
  plotTop: 50,
  task: { backend: "codexcli", repoPath: "owner/repo", status: "STARTED" },
  schedule: null,
  floatingNumbers: [],
  onSelect: vi.fn(),
};

describe("WorkerSprite component", () => {
  it("renders bot variant with correct sprite parts", () => {
    const { container } = render(<WorkerSprite {...BASE_WORKER_PROPS} />);
    expect(container.querySelector(".worker-sprite.active")).toBeTruthy();
    expect(container.querySelector(".worker-art.bot-alpha")).toBeTruthy();
    expect(container.querySelector(".bot-head")).toBeTruthy();
    expect(container.querySelector(".bot-torso")).toBeTruthy();
    expect(container.querySelector(".bot-arm.bot-arm-left")).toBeTruthy();
    expect(container.querySelector(".bot-leg.bot-leg-right")).toBeTruthy();
    // Should NOT have goose parts
    expect(container.querySelector(".goose-body")).toBeNull();
  });

  it("renders goose variant with correct sprite parts", () => {
    const { container } = render(
      <WorkerSprite
        {...BASE_WORKER_PROPS}
        style={GOOSE_STYLE}
        spriteVariant="goose"
        provider="goose"
      />
    );
    expect(container.querySelector(".worker-art.goose")).toBeTruthy();
    expect(container.querySelector(".goose-body")).toBeTruthy();
    expect(container.querySelector(".goose-beak")).toBeTruthy();
    expect(container.querySelector(".goose-leg.goose-leg-left")).toBeTruthy();
    // Should NOT have bot parts
    expect(container.querySelector(".bot-head")).toBeNull();
  });

  it("applies selected class when isSelected is true", () => {
    const { container } = render(
      <WorkerSprite {...BASE_WORKER_PROPS} isSelected />
    );
    expect(container.querySelector(".worker-sprite.selected")).toBeTruthy();
  });

  it("does not apply selected class when isSelected is false", () => {
    const { container } = render(
      <WorkerSprite {...BASE_WORKER_PROPS} isSelected={false} />
    );
    expect(container.querySelector(".worker-sprite.selected")).toBeNull();
  });

  it("renders floating numbers", () => {
    const floats = [
      { id: 1, taskId: "abc-123", value: 5, createdAt: Date.now() },
      { id: 2, taskId: "abc-123", value: 3, createdAt: Date.now() },
    ];
    const { container } = render(
      <WorkerSprite {...BASE_WORKER_PROPS} floatingNumbers={floats} />
    );
    const nums = container.querySelectorAll(".floating-number");
    expect(nums.length).toBe(2);
    expect(nums[0].textContent).toBe("+5");
    expect(nums[1].textContent).toBe("+3");
  });

  it("renders worker caption with repo name and provider", () => {
    const { container } = render(<WorkerSprite {...BASE_WORKER_PROPS} />);
    const caption = container.querySelector(".worker-caption");
    expect(caption).toBeTruthy();
    expect(caption?.querySelector(".worker-repo")?.textContent).toBe("repo");
    expect(caption?.textContent).toContain("STARTED");
  });

  it("renders schedule cron label when schedule is provided", () => {
    const { container } = render(
      <WorkerSprite
        {...BASE_WORKER_PROPS}
        schedule={{ name: "nightly", cron_expression: "0 0 * * *" }}
      />
    );
    const cron = container.querySelector(".worker-cron");
    expect(cron).toBeTruthy();
  });

  it("calls onSelect with taskId when clicked", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <WorkerSprite {...BASE_WORKER_PROPS} onSelect={onSelect} />
    );
    const btn = container.querySelector(".worker-sprite") as HTMLButtonElement;
    fireEvent.click(btn);
    expect(onSelect).toHaveBeenCalledWith("abc-123");
  });

  it("is disabled when isActive is false", () => {
    const { container } = render(
      <WorkerSprite {...BASE_WORKER_PROPS} isActive={false} />
    );
    const btn = container.querySelector(".worker-sprite") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("positions at torii gate when phase is at-gate", () => {
    const { container } = render(
      <WorkerSprite {...BASE_WORKER_PROPS} phase="at-gate" />
    );
    const btn = container.querySelector(".worker-sprite") as HTMLElement;
    expect(btn.style.left).toBe(`${TORII_POS.left}%`);
    expect(btn.style.top).toBe(`${TORII_POS.top}%`);
  });

  it("positions at plot when phase is meditating", () => {
    const { container } = render(
      <WorkerSprite {...BASE_WORKER_PROPS} phase="meditating" plotLeft={40} plotTop={50} />
    );
    const btn = container.querySelector(".worker-sprite") as HTMLElement;
    expect(btn.style.left).toBe("40%");
    expect(btn.style.top).toBe("50%");
  });

  it("positions at plot when phase is fading", () => {
    const { container } = render(
      <WorkerSprite {...BASE_WORKER_PROPS} phase="fading" plotLeft={40} plotTop={50} />
    );
    const btn = container.querySelector(".worker-sprite") as HTMLElement;
    expect(btn.style.left).toBe("40%");
    expect(btn.style.top).toBe("50%");
  });

  it("positions at plot when phase is active", () => {
    const { container } = render(
      <WorkerSprite {...BASE_WORKER_PROPS} phase="active" plotLeft={60} plotTop={70} />
    );
    const btn = container.querySelector(".worker-sprite") as HTMLElement;
    expect(btn.style.left).toBe("60%");
    expect(btn.style.top).toBe("70%");
  });
});
