import { describe, expect, it } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import PlayerAvatar from "./PlayerAvatar";
import { EMOTE_MAP } from "../constants";

describe("PlayerAvatar component", () => {
  it("renders local player with correct class and aria-label", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal x={50} y={50} />
    );
    const el = container.querySelector(".human-player.down");
    expect(el).toBeTruthy();
    expect(el?.getAttribute("aria-label")).toBe("You (player character)");
    // Should NOT have remote-player-name
    expect(container.querySelector(".remote-player-name")).toBeNull();
  });

  it("renders remote player with name and colour CSS variables", () => {
    const { container } = render(
      <PlayerAvatar
        direction="left"
        walking={true}
        name="Alice"
        color="#e11d48"
        x={30}
        y={40}
      />
    );
    const el = container.querySelector(".remote-player.left.walking");
    expect(el).toBeTruthy();
    expect(el?.getAttribute("aria-label")).toBe("Alice");
    // Name label rendered
    const nameEl = container.querySelector(".remote-player-name");
    expect(nameEl?.textContent).toBe("Alice");
    // CSS variables set
    expect((el as HTMLElement).style.getPropertyValue("--rp-body")).toBe(
      "#e11d48"
    );
  });

  it("renders emote bubble when emote prop is set", () => {
    const { container } = render(
      <PlayerAvatar direction="up" walking={false} isLocal emote="wave" x={50} y={50} />
    );
    const bubble = container.querySelector(".emote-bubble");
    expect(bubble).toBeTruthy();
    expect(bubble?.textContent).toBe(EMOTE_MAP.wave);
  });

  it("does not render emote bubble when emote is null", () => {
    const { container } = render(
      <PlayerAvatar direction="right" walking={false} isLocal emote={null} x={50} y={50} />
    );
    expect(container.querySelector(".emote-bubble")).toBeNull();
  });

  it("renders the full human-body sprite tree", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal x={50} y={50} />
    );
    const body = container.querySelector(".human-body");
    expect(body).toBeTruthy();
    expect(body?.querySelector(".human-helmet")).toBeTruthy();
    expect(body?.querySelector(".human-visor")).toBeTruthy();
    expect(body?.querySelector(".human-torso")).toBeTruthy();
    expect(body?.querySelector(".human-arm.human-arm-left")).toBeTruthy();
    expect(body?.querySelector(".human-arm.human-arm-right")).toBeTruthy();
    expect(body?.querySelector(".human-leg.human-leg-left")).toBeTruthy();
    expect(body?.querySelector(".human-leg.human-leg-right")).toBeTruthy();
    expect(body?.querySelector(".human-boot.human-boot-left")).toBeTruthy();
    expect(body?.querySelector(".human-boot.human-boot-right")).toBeTruthy();
  });

  it("sets position via inline styles", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal x={25} y={75} />
    );
    const el = container.querySelector(".human-player") as HTMLElement;
    expect(el.style.left).toBe("25%");
    expect(el.style.top).toBe("75%");
  });

  it("renders chat bubble when chat prop is set", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal chat="Hello!" x={50} y={50} />
    );
    const bubble = container.querySelector(".chat-bubble");
    expect(bubble).toBeTruthy();
    expect(bubble?.textContent).toBe("Hello!");
    expect(bubble?.getAttribute("aria-label")).toBe("Chat: Hello!");
  });

  it("does not render chat bubble when chat is null", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal chat={null} x={50} y={50} />
    );
    expect(container.querySelector(".chat-bubble")).toBeNull();
  });

  it("renders idle indicator when idle is true", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal idle={true} x={50} y={50} />
    );
    const indicator = container.querySelector(".idle-indicator");
    expect(indicator).toBeTruthy();
    expect(indicator?.textContent).toBe("zzz");
    expect(indicator?.getAttribute("aria-label")).toBe("Idle");
  });

  it("does not render idle indicator when idle is false", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal idle={false} x={50} y={50} />
    );
    expect(container.querySelector(".idle-indicator")).toBeNull();
  });

  it("hides idle indicator when emote is active", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal idle={true} emote="wave" x={50} y={50} />
    );
    expect(container.querySelector(".idle-indicator")).toBeNull();
    expect(container.querySelector(".emote-bubble")).toBeTruthy();
  });

  it("hides idle indicator when chat is active", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal idle={true} chat="Hello!" x={50} y={50} />
    );
    expect(container.querySelector(".idle-indicator")).toBeNull();
    expect(container.querySelector(".chat-bubble")).toBeTruthy();
  });

  it("renders typing indicator when typing is true", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal typing={true} x={50} y={50} />
    );
    const indicator = container.querySelector(".typing-indicator");
    expect(indicator).toBeTruthy();
    expect(indicator?.textContent).toBe("...");
    expect(indicator?.getAttribute("aria-label")).toBe("Typing");
  });

  it("does not render typing indicator when typing is false", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal typing={false} x={50} y={50} />
    );
    expect(container.querySelector(".typing-indicator")).toBeNull();
  });

  it("hides typing indicator when emote is active", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal typing={true} emote="wave" x={50} y={50} />
    );
    expect(container.querySelector(".typing-indicator")).toBeNull();
    expect(container.querySelector(".emote-bubble")).toBeTruthy();
  });

  it("hides typing indicator when chat is active", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal typing={true} chat="Hello!" x={50} y={50} />
    );
    expect(container.querySelector(".typing-indicator")).toBeNull();
    expect(container.querySelector(".chat-bubble")).toBeTruthy();
  });

  it("typing indicator suppresses idle indicator", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal typing={true} idle={true} x={50} y={50} />
    );
    expect(container.querySelector(".typing-indicator")).toBeTruthy();
    expect(container.querySelector(".idle-indicator")).toBeNull();
  });

  // --- Tooltip tests ---

  it("shows tooltip on hover for remote player", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} name="Alice" color="#e11d48" x={30} y={40} />
    );
    const el = container.querySelector(".remote-player")!;
    expect(container.querySelector(".player-tooltip")).toBeNull();
    fireEvent.mouseEnter(el);
    const tooltip = container.querySelector(".player-tooltip");
    expect(tooltip).toBeTruthy();
    expect(container.querySelector(".player-tooltip-name")?.textContent).toBe("Alice");
    expect(container.querySelector(".player-tooltip-status")?.textContent).toBe("active");
  });

  it("hides tooltip on mouse leave for remote player", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} name="Bob" color="#2563eb" x={50} y={50} />
    );
    const el = container.querySelector(".remote-player")!;
    fireEvent.mouseEnter(el);
    expect(container.querySelector(".player-tooltip")).toBeTruthy();
    fireEvent.mouseLeave(el);
    expect(container.querySelector(".player-tooltip")).toBeNull();
  });

  it("does not show tooltip for local player on hover", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} isLocal x={50} y={50} />
    );
    const el = container.querySelector(".human-player")!;
    fireEvent.mouseEnter(el);
    expect(container.querySelector(".player-tooltip")).toBeNull();
  });

  it("shows typing status in tooltip when player is typing", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} name="Typer" color="#16a34a" typing={true} x={30} y={40} />
    );
    fireEvent.mouseEnter(container.querySelector(".remote-player")!);
    expect(container.querySelector(".player-tooltip-status")?.textContent).toBe("typing");
    expect(container.querySelector(".player-tooltip-status-typing")).toBeTruthy();
  });

  it("shows idle status in tooltip when player is idle", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} name="Idler" color="#94a3b8" idle={true} x={30} y={40} />
    );
    fireEvent.mouseEnter(container.querySelector(".remote-player")!);
    expect(container.querySelector(".player-tooltip-status")?.textContent).toBe("idle");
  });

  it("shows walking status in tooltip when player is walking", () => {
    const { container } = render(
      <PlayerAvatar direction="right" walking={true} name="Walker" color="#e74c3c" x={30} y={40} />
    );
    fireEvent.mouseEnter(container.querySelector(".remote-player")!);
    expect(container.querySelector(".player-tooltip-status")?.textContent).toBe("walking");
  });

  it("renders color indicator in tooltip matching player color", () => {
    const { container } = render(
      <PlayerAvatar direction="down" walking={false} name="ColorTest" color="#f59e0b" x={30} y={40} />
    );
    fireEvent.mouseEnter(container.querySelector(".remote-player")!);
    const dot = container.querySelector(".player-tooltip-color") as HTMLElement;
    expect(dot).toBeTruthy();
    expect(dot.style.backgroundColor).toBe("rgb(245, 158, 11)");
  });
});
