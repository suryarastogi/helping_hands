import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";

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
});
