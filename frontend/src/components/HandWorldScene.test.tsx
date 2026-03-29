import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import HandWorldScene from "./HandWorldScene";
import type { SceneWorkerEntry } from "./HandWorldScene";
import type { RemoteCursor, RemotePlayer } from "../hooks/useMultiplayer";
import type { ClaudeUsageResponse, FloatingNumber, WorldDecoration } from "../types";

const BOT_STYLE = {
  bodyColor: "#10a37f",
  accentColor: "#c7fff1",
  skinColor: "#d9f6ef",
  outlineColor: "#0b3e32",
  variant: "bot-alpha" as const,
};

const SCENE_DESK_SLOTS = [
  { id: "desk-0", left: 30, top: 30 },
  { id: "desk-1", left: 60, top: 30 },
];

const SCENE_WORKER_ENTRY: SceneWorkerEntry = {
  taskId: "w-1",
  slot: 0,
  phase: "active",
  phaseChangedAt: Date.now(),
  task: { backend: "codexcli", repoPath: "owner/repo", status: "STARTED" },
  desk: SCENE_DESK_SLOTS[0],
  isActive: true,
  provider: "openai",
  style: BOT_STYLE,
  spriteVariant: "bot-alpha",
  schedule: null,
};

const BASE_SCENE_PROPS = {
  sceneRef: { current: null } as React.RefObject<HTMLDivElement | null>,
  sceneStyle: { minHeight: "380px" },
  maxWorkers: 8,
  deskSlots: SCENE_DESK_SLOTS,
  workerEntries: [] as SceneWorkerEntry[],
  selectedTaskId: null as string | null,
  onSelectTask: vi.fn(),
  playerDirection: "down" as const,
  isPlayerWalking: false,
  playerPosition: { x: 50, y: 50 },
  localEmote: null as string | null,
  remotePlayers: [] as RemotePlayer[],
  remoteEmotes: {} as Record<string, string>,
  remoteChats: {} as Record<string, string>,
  remoteTyping: {} as Record<string, boolean>,
  localChat: null as string | null,
  isLocalIdle: false,
  isLocalTyping: false,
  connectionStatus: "connected" as const,
  claudeUsage: null as ClaudeUsageResponse | null,
  claudeUsageLoading: false,
  onRefreshClaudeUsage: vi.fn(),
  floatingNumbers: [] as FloatingNumber[],
  decorations: [] as WorldDecoration[],
  onPlaceDecoration: vi.fn(),
  onClearDecorations: vi.fn(),
  decoOnCooldown: false,
  remoteCursors: [] as RemoteCursor[],
  onCursorMove: vi.fn(),
};

describe("HandWorldScene component", () => {
  it("renders the scene container with header", () => {
    const { container } = render(<HandWorldScene {...BASE_SCENE_PROPS} />);
    expect(container.querySelector(".hand-world-card")).toBeTruthy();
    expect(container.querySelector("h1")?.textContent).toContain("Hand World");
    expect(container.querySelector(".world-scene.office-scene")).toBeTruthy();
  });

  it("renders zen garden decorations", () => {
    const { container } = render(<HandWorldScene {...BASE_SCENE_PROPS} />);
    expect(container.querySelector(".zen-sky")).toBeTruthy();
    expect(container.querySelector(".zen-bamboo")).toBeTruthy();
    expect(container.querySelector(".zen-maple")).toBeTruthy();
    expect(container.querySelector(".zen-lantern")).toBeTruthy();
    expect(container.querySelector(".zen-rock.zen-rock-lg")).toBeTruthy();
  });

  it("renders factory and incinerator", () => {
    const { container } = render(<HandWorldScene {...BASE_SCENE_PROPS} />);
    expect(container.querySelector(".hh-factory")).toBeTruthy();
    expect(container.querySelector(".factory-label")?.textContent).toBe("FACTORY");
    expect(container.querySelector(".hh-incinerator")).toBeTruthy();
    expect(container.querySelector(".incinerator-label")?.textContent).toBe("INCINERATOR");
  });

  it("renders desk slots at correct positions", () => {
    const { container } = render(<HandWorldScene {...BASE_SCENE_PROPS} />);
    const desks = container.querySelectorAll(".work-desk");
    expect(desks.length).toBe(2);
    expect((desks[0] as HTMLElement).style.left).toBe("30%");
    expect((desks[0] as HTMLElement).style.top).toBe("30%");
    expect((desks[1] as HTMLElement).style.left).toBe("60%");
    expect((desks[1] as HTMLElement).style.top).toBe("30%");
  });

  it("renders local player avatar", () => {
    const { container } = render(<HandWorldScene {...BASE_SCENE_PROPS} />);
    const player = container.querySelector(".human-player");
    expect(player).toBeTruthy();
    expect(player?.getAttribute("aria-label")).toBe("You (player character)");
  });

  it("renders remote players", () => {
    const props = {
      ...BASE_SCENE_PROPS,
      remotePlayers: [
        { player_id: "r1", name: "Alice", color: "#e11d48", x: 30, y: 40, direction: "left" as const, walking: false, idle: false },
      ],
    };
    const { container } = render(<HandWorldScene {...props} />);
    const remote = container.querySelector(".remote-player");
    expect(remote).toBeTruthy();
    expect(container.querySelector(".remote-player-name")?.textContent).toBe("Alice");
  });

  it("renders worker sprites for workerEntries", () => {
    const props = {
      ...BASE_SCENE_PROPS,
      workerEntries: [SCENE_WORKER_ENTRY],
    };
    const { container } = render(<HandWorldScene {...props} />);
    expect(container.querySelector(".worker-sprite")).toBeTruthy();
  });

  it("renders status summary with station count", () => {
    const { container } = render(<HandWorldScene {...BASE_SCENE_PROPS} />);
    const summary = container.querySelector(".zen-status-summary");
    expect(summary).toBeTruthy();
    expect(summary?.textContent).toContain("8 Stations");
    expect(summary?.textContent).toContain("0 Active");
  });

  it("shows connection status hint for connected state", () => {
    const { container } = render(<HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" />);
    const hint = container.querySelector(".status-summary-hint");
    expect(hint?.textContent).toContain("Multiplayer active");
  });

  it("shows connection status hint for disconnected state", () => {
    const { container } = render(<HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="disconnected" />);
    const hint = container.querySelector(".status-summary-hint");
    expect(hint?.textContent).toContain("Disconnected");
  });

  it("renders Claude usage meters when usage data provided", () => {
    const usage = {
      levels: [
        { name: "Tier 1", percent_used: 45, detail: "" },
        { name: "Tier 2", percent_used: 80, detail: "" },
      ],
      error: null,
      fetched_at: "2026-03-23T00:00:00Z",
    };
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} claudeUsage={usage} />
    );
    const meters = container.querySelectorAll(".usage-meter-row");
    expect(meters.length).toBe(2);
    expect(container.querySelector(".usage-meter-label")?.textContent).toBe("Tier 1");
  });

  it("shows desk monitor when occupant is active", () => {
    const props = {
      ...BASE_SCENE_PROPS,
      workerEntries: [SCENE_WORKER_ENTRY],
    };
    const { container } = render(<HandWorldScene {...props} />);
    expect(container.querySelector(".desk-monitor.monitor-on")).toBeTruthy();
  });

  it("passes localChat to local player avatar", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} localChat="Hi there" />
    );
    const bubble = container.querySelector(".human-player .chat-bubble");
    expect(bubble).toBeTruthy();
    expect(bubble?.textContent).toBe("Hi there");
  });

  it("passes remoteChats to remote player avatars", () => {
    const props = {
      ...BASE_SCENE_PROPS,
      remotePlayers: [
        { player_id: "r1", name: "Alice", color: "#e11d48", x: 30, y: 40, direction: "left" as const, walking: false, idle: false },
      ],
      remoteChats: { r1: "Hey!" },
    };
    const { container } = render(<HandWorldScene {...props} />);
    const bubble = container.querySelector(".remote-player .chat-bubble");
    expect(bubble).toBeTruthy();
    expect(bubble?.textContent).toBe("Hey!");
  });

  it("renders usage loading placeholder when loading and no data", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} claudeUsageLoading={true} claudeUsage={null} />
    );
    expect(container.querySelector(".usage-placeholder")?.textContent).toBe("Loading...");
  });

  it("renders usage error message", () => {
    const usage = { levels: [], error: "API key missing", fetched_at: "" };
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} claudeUsage={usage} />
    );
    expect(container.querySelector(".usage-error")?.textContent).toBe("API key missing");
  });

  it("renders click-to-load placeholder when no data and not loading", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} claudeUsage={null} claudeUsageLoading={false} />
    );
    const placeholder = container.querySelector(".usage-placeholder");
    expect(placeholder).toBeTruthy();
    expect(placeholder?.textContent).toContain("Click");
    expect(placeholder?.textContent).toContain("to load");
  });

  it("applies warn/crit classes to usage meters based on percentage", () => {
    const usage = {
      levels: [
        { name: "Low", percent_used: 40, detail: "" },
        { name: "Warn", percent_used: 75, detail: "" },
        { name: "Crit", percent_used: 95, detail: "" },
      ],
      error: null,
      fetched_at: "2026-03-23T00:00:00Z",
    };
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} claudeUsage={usage} />
    );
    const fills = container.querySelectorAll(".usage-meter-fill");
    expect(fills).toHaveLength(3);
    expect(fills[0].classList.contains("warn")).toBe(false);
    expect(fills[0].classList.contains("crit")).toBe(false);
    expect(fills[1].classList.contains("warn")).toBe(true);
    expect(fills[2].classList.contains("crit")).toBe(true);
  });

  it("shows connecting status hint", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connecting" />
    );
    const hint = container.querySelector(".status-summary-hint");
    expect(hint?.textContent).toContain("Connecting");
  });

  it("renders desk monitor for walking-to-desk phase", () => {
    const walkingEntry: SceneWorkerEntry = {
      ...SCENE_WORKER_ENTRY,
      phase: "walking-to-desk",
    };
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} workerEntries={[walkingEntry]} />
    );
    expect(container.querySelector(".desk-monitor")).toBeTruthy();
    expect(container.querySelector(".desk-monitor.monitor-on")).toBeNull();
  });

  it("passes isLocalIdle to local player avatar", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} isLocalIdle={true} />
    );
    const indicator = container.querySelector(".human-player .idle-indicator");
    expect(indicator).toBeTruthy();
    expect(indicator?.textContent).toBe("zzz");
  });

  it("shows player count badge when connected", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" remotePlayers={[]} />
    );
    const badge = container.querySelector(".player-count-badge");
    expect(badge).toBeTruthy();
    expect(badge?.textContent).toBe("1");
    expect(badge?.getAttribute("aria-label")).toBe("1 players online");
  });

  it("shows correct count with remote players", () => {
    const remotes: RemotePlayer[] = [
      { player_id: "r1", name: "Alice", color: "#e11d48", x: 30, y: 30, direction: "down", walking: false, idle: false },
      { player_id: "r2", name: "Bob", color: "#2563eb", x: 60, y: 60, direction: "up", walking: true, idle: false },
    ];
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" remotePlayers={remotes} />
    );
    const badge = container.querySelector(".player-count-badge");
    expect(badge).toBeTruthy();
    expect(badge?.textContent).toBe("3");
    expect(badge?.getAttribute("aria-label")).toBe("3 players online");
  });

  it("hides player count badge when disconnected", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="disconnected" />
    );
    const badge = container.querySelector(".player-count-badge");
    expect(badge).toBeNull();
  });

  it("hides player count badge when connecting", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connecting" />
    );
    const badge = container.querySelector(".player-count-badge");
    expect(badge).toBeNull();
  });

  // --- Typing indicator ---

  it("passes isLocalTyping to local player avatar", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} isLocalTyping={true} />
    );
    const indicator = container.querySelector(".human-player .typing-indicator");
    expect(indicator).toBeTruthy();
    expect(indicator?.textContent).toBe("...");
  });

  it("passes remoteTyping to remote player avatars", () => {
    const props = {
      ...BASE_SCENE_PROPS,
      remotePlayers: [
        { player_id: "r1", name: "Alice", color: "#e11d48", x: 30, y: 40, direction: "left" as const, walking: false, idle: false, typing: false },
      ],
      remoteTyping: { r1: true },
    };
    const { container } = render(<HandWorldScene {...props} />);
    const indicator = container.querySelector(".remote-player .typing-indicator");
    expect(indicator).toBeTruthy();
  });

  // --- Minimap ---

  it("renders minimap when connected", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" />
    );
    expect(container.querySelector(".minimap")).toBeTruthy();
  });

  it("hides minimap when disconnected", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="disconnected" />
    );
    expect(container.querySelector(".minimap")).toBeNull();
  });

  it("renders minimap with local player dot", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" playerPosition={{ x: 30, y: 70 }} />
    );
    const localDot = container.querySelector(".minimap-dot-local");
    expect(localDot).toBeTruthy();
    expect((localDot as HTMLElement).style.left).toBe("30%");
    expect((localDot as HTMLElement).style.top).toBe("70%");
  });

  it("renders minimap with remote player dots", () => {
    const remotes: RemotePlayer[] = [
      { player_id: "r1", name: "Alice", color: "#e11d48", x: 20, y: 40, direction: "down", walking: false, idle: false },
    ];
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" remotePlayers={remotes} />
    );
    const remoteDots = container.querySelectorAll(".minimap-dot-remote");
    expect(remoteDots).toHaveLength(1);
  });

  it("renders minimap worker dots for active workers", () => {
    const props = {
      ...BASE_SCENE_PROPS,
      connectionStatus: "connected" as const,
      workerEntries: [SCENE_WORKER_ENTRY],
    };
    const { container } = render(<HandWorldScene {...props} />);
    const workerDots = container.querySelectorAll(".minimap-dot-worker");
    expect(workerDots).toHaveLength(1);
  });

  // --- Reconnection banner ---

  it("shows reconnect banner when connectionStatus is connecting", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connecting" />
    );
    const banner = container.querySelector(".reconnect-banner");
    expect(banner).toBeTruthy();
    expect(banner?.getAttribute("role")).toBe("alert");
    expect(banner?.textContent).toContain("Reconnecting");
    expect(container.querySelector(".reconnect-spinner")).toBeTruthy();
  });

  it("hides reconnect banner when connected", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" />
    );
    expect(container.querySelector(".reconnect-banner")).toBeNull();
  });

  it("hides reconnect banner when disconnected", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="disconnected" />
    );
    expect(container.querySelector(".reconnect-banner")).toBeNull();
  });

  it("shows connection failed banner when status is failed", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="failed" />
    );
    const banner = container.querySelector(".reconnect-banner.reconnect-failed");
    expect(banner).toBeTruthy();
    expect(banner?.getAttribute("role")).toBe("alert");
    expect(banner?.textContent).toContain("Connection failed");
  });

  it("shows 'Connection failed' in status hint when status is failed", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="failed" />
    );
    const hint = container.querySelector(".status-summary-hint");
    expect(hint?.textContent).toContain("Connection failed");
  });

  // --- Shared decorations ---

  it("renders decoration toolbar when connected", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" />
    );
    const toolbar = container.querySelector(".decoration-toolbar");
    expect(toolbar).toBeTruthy();
    expect(toolbar?.getAttribute("aria-label")).toBe("Decoration toolbar");
  });

  it("hides decoration toolbar when disconnected", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="disconnected" />
    );
    expect(container.querySelector(".decoration-toolbar")).toBeNull();
  });

  it("renders decoration emoji palette with correct count", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" />
    );
    const buttons = container.querySelectorAll(".decoration-emoji-btn");
    expect(buttons.length).toBe(8);
  });

  it("shows decoration count in toolbar header", () => {
    const decos: WorldDecoration[] = [
      { id: "d1", emoji: "\u{1F338}", x: 30, y: 40, placedBy: "Alice", color: "#e11d48", placedAt: 1000 },
      { id: "d2", emoji: "\u{2B50}", x: 50, y: 60, placedBy: "Bob", color: "#2563eb", placedAt: 2000 },
    ];
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" decorations={decos} />
    );
    const header = container.querySelector(".decoration-toolbar-header");
    expect(header?.textContent).toContain("2/20");
  });

  it("renders world decoration elements at correct positions", () => {
    const decos: WorldDecoration[] = [
      { id: "d1", emoji: "\u{1F338}", x: 25, y: 45, placedBy: "Alice", color: "#e11d48", placedAt: 1000 },
    ];
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} decorations={decos} />
    );
    const deco = container.querySelector(".world-decoration") as HTMLElement;
    expect(deco).toBeTruthy();
    expect(deco.textContent).toBe("\u{1F338}");
    expect(deco.style.left).toBe("25%");
    expect(deco.style.top).toBe("45%");
    expect(deco.title).toBe("Placed by Alice");
  });

  it("shows clear button when decorations exist", () => {
    const decos: WorldDecoration[] = [
      { id: "d1", emoji: "\u{1F338}", x: 30, y: 40, placedBy: "Alice", color: "#e11d48", placedAt: 1000 },
    ];
    const onClear = vi.fn();
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" decorations={decos} onClearDecorations={onClear} />
    );
    const clearBtn = container.querySelector(".decoration-clear-btn");
    expect(clearBtn).toBeTruthy();
    fireEvent.click(clearBtn!);
    expect(onClear).toHaveBeenCalled();
  });

  it("hides clear button when no decorations", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" decorations={[]} />
    );
    expect(container.querySelector(".decoration-clear-btn")).toBeNull();
  });

  it("selects emoji and shows placement hint on click", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" />
    );
    const buttons = container.querySelectorAll(".decoration-emoji-btn");
    fireEvent.click(buttons[0]);
    expect(buttons[0].classList.contains("selected")).toBe(true);
    expect(buttons[0].getAttribute("aria-pressed")).toBe("true");
    expect(container.querySelector(".decoration-hint")).toBeTruthy();
    expect(container.querySelector(".decoration-hint")?.textContent).toContain("Double-click");
  });

  it("deselects emoji on second click", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" />
    );
    const buttons = container.querySelectorAll(".decoration-emoji-btn");
    fireEvent.click(buttons[0]);
    expect(buttons[0].classList.contains("selected")).toBe(true);
    fireEvent.click(buttons[0]);
    expect(buttons[0].classList.contains("selected")).toBe(false);
    expect(container.querySelector(".decoration-hint")).toBeNull();
  });

  it("adds deco-placing class to scene when emoji selected", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" />
    );
    const scene = container.querySelector(".world-scene");
    expect(scene?.classList.contains("deco-placing")).toBe(false);
    const buttons = container.querySelectorAll(".decoration-emoji-btn");
    fireEvent.click(buttons[0]);
    expect(scene?.classList.contains("deco-placing")).toBe(true);
  });

  it("disables decoration emoji buttons during cooldown", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" decoOnCooldown={true} />
    );
    const buttons = container.querySelectorAll(".decoration-emoji-btn");
    expect(buttons.length).toBeGreaterThan(0);
    buttons.forEach((btn) => {
      expect((btn as HTMLButtonElement).disabled).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // Remote cursor rendering
  // -------------------------------------------------------------------------

  it("renders remote cursors with name and color", () => {
    const cursors: RemoteCursor[] = [
      { player_id: "99", name: "Alice", color: "#e11d48", x: 30, y: 40 },
      { player_id: "100", name: "Bob", color: "#2563eb", x: 70, y: 60 },
    ];
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} remoteCursors={cursors} />
    );
    const cursorEls = container.querySelectorAll(".remote-cursor");
    expect(cursorEls.length).toBe(2);
    expect(cursorEls[0].getAttribute("aria-label")).toBe("Alice's cursor");
    expect(cursorEls[1].getAttribute("aria-label")).toBe("Bob's cursor");

    // Check labels
    const labels = container.querySelectorAll(".remote-cursor-label");
    expect(labels[0].textContent).toBe("Alice");
    expect(labels[1].textContent).toBe("Bob");
  });

  it("does not render cursors when list is empty", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} remoteCursors={[]} />
    );
    expect(container.querySelectorAll(".remote-cursor").length).toBe(0);
  });

  it("calls onCursorMove on mouse move over scene", () => {
    const onCursorMove = vi.fn();
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} onCursorMove={onCursorMove} />
    );
    const scene = container.querySelector(".world-scene")!;
    // Mock getBoundingClientRect for percentage calculation
    vi.spyOn(scene, "getBoundingClientRect").mockReturnValue({
      left: 0, top: 0, width: 1000, height: 500,
      right: 1000, bottom: 500, x: 0, y: 0, toJSON: () => ({}),
    });
    fireEvent.mouseMove(scene, { clientX: 500, clientY: 250 });
    expect(onCursorMove).toHaveBeenCalledWith({ x: 50, y: 50 });
  });

  it("calls onCursorMove(null) on mouse leave", () => {
    const onCursorMove = vi.fn();
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} onCursorMove={onCursorMove} />
    );
    const scene = container.querySelector(".world-scene")!;
    fireEvent.mouseLeave(scene);
    expect(onCursorMove).toHaveBeenCalledWith(null);
  });

  // -------------------------------------------------------------------------
  // Accessibility — aria-live on banners, aria-label on refresh button
  // -------------------------------------------------------------------------

  it("reconnect banner has aria-live=polite for screen reader announcements", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connecting" />
    );
    const banner = container.querySelector(".reconnect-banner");
    expect(banner?.getAttribute("aria-live")).toBe("polite");
  });

  it("connection failed banner has aria-live=assertive", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="failed" />
    );
    const banner = container.querySelector(".reconnect-banner.reconnect-failed");
    expect(banner?.getAttribute("aria-live")).toBe("assertive");
  });

  it("refresh usage button has aria-label", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} showClaudeUsage />
    );
    const btn = container.querySelector(".usage-refresh-btn");
    expect(btn?.getAttribute("aria-label")).toBe("Refresh Claude usage");
  });
});
