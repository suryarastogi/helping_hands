import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import HandWorldScene from "./HandWorldScene";
import type { SceneWorkerEntry } from "./HandWorldScene";
import type { RemotePlayer } from "../hooks/useMultiplayer";
import type { ChatMessage, ClaudeUsageResponse, FloatingNumber } from "../types";

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
  localChat: null as string | null,
  isLocalIdle: false,
  connectionStatus: "connected" as const,
  chatHistory: [] as ChatMessage[],
  onSendChat: vi.fn(),
  playerNameInput: "Tester",
  onPlayerNameChange: vi.fn(),
  claudeUsage: null as ClaudeUsageResponse | null,
  claudeUsageLoading: false,
  onRefreshClaudeUsage: vi.fn(),
  floatingNumbers: [] as FloatingNumber[],
};

describe("HandWorldScene component", () => {
  it("renders the scene container with header", () => {
    const { container } = render(<HandWorldScene {...BASE_SCENE_PROPS} />);
    expect(container.querySelector(".hand-world-card")).toBeTruthy();
    expect(container.querySelector("h1")?.textContent).toBe("Hand World");
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

  it("renders presence panel when remote players exist", () => {
    const props = {
      ...BASE_SCENE_PROPS,
      remotePlayers: [
        { player_id: "r1", name: "Bob", color: "#2563eb", x: 60, y: 60, direction: "right" as const, walking: true, idle: false },
      ],
    };
    const { container } = render(<HandWorldScene {...props} />);
    const panel = container.querySelector(".presence-panel");
    expect(panel).toBeTruthy();
    expect(panel?.textContent).toContain("2 Online");
    expect(container.querySelector(".presence-name")?.textContent).toBe("Bob");
  });

  it("hides presence panel when no remote players", () => {
    const { container } = render(<HandWorldScene {...BASE_SCENE_PROPS} />);
    expect(container.querySelector(".presence-panel")).toBeNull();
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

  it("calls onPlayerNameChange when name input changes", () => {
    const onNameChange = vi.fn();
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} onPlayerNameChange={onNameChange} />
    );
    const input = container.querySelector(".player-name-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "NewName" } });
    expect(onNameChange).toHaveBeenCalledWith("NewName");
  });

  it("renders chat input when connected", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="connected" />
    );
    const chatInput = container.querySelector(".chat-input");
    expect(chatInput).toBeTruthy();
    expect(chatInput?.getAttribute("aria-label")).toBe("Chat message");
  });

  it("hides chat input when disconnected", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} connectionStatus="disconnected" />
    );
    expect(container.querySelector(".chat-input")).toBeNull();
  });

  it("calls onSendChat on chat form submit", () => {
    const onSendChat = vi.fn();
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} onSendChat={onSendChat} />
    );
    const input = container.querySelector(".chat-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Hello world" } });
    fireEvent.submit(container.querySelector(".chat-input-form")!);
    expect(onSendChat).toHaveBeenCalledWith("Hello world");
    expect(input.value).toBe("");
  });

  it("does not call onSendChat for empty messages", () => {
    const onSendChat = vi.fn();
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} onSendChat={onSendChat} />
    );
    fireEvent.submit(container.querySelector(".chat-input-form")!);
    expect(onSendChat).not.toHaveBeenCalled();
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

  // --- Chat history panel ---

  it("renders chat history panel when messages exist", () => {
    const messages: ChatMessage[] = [
      { id: "m1", playerName: "Alice", playerColor: "#e11d48", text: "Hello!", timestamp: 1000 },
      { id: "m2", playerName: "Bob", playerColor: "#2563eb", text: "Hi Alice!", timestamp: 2000 },
    ];
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} chatHistory={messages} />
    );
    const panel = container.querySelector(".chat-history-panel");
    expect(panel).toBeTruthy();
    expect(panel?.getAttribute("aria-label")).toBe("Chat history");

    const msgElements = container.querySelectorAll(".chat-history-message");
    expect(msgElements).toHaveLength(2);

    const names = container.querySelectorAll(".chat-history-name");
    expect(names[0].textContent).toBe("Alice");
    expect(names[1].textContent).toBe("Bob");

    const texts = container.querySelectorAll(".chat-history-text");
    expect(texts[0].textContent).toBe("Hello!");
    expect(texts[1].textContent).toBe("Hi Alice!");
  });

  it("hides chat history panel when no messages", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} chatHistory={[]} />
    );
    expect(container.querySelector(".chat-history-panel")).toBeNull();
  });

  it("applies player color to chat history names", () => {
    const messages: ChatMessage[] = [
      { id: "m1", playerName: "ColorTest", playerColor: "#16a34a", text: "Green", timestamp: 1000 },
    ];
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} chatHistory={messages} />
    );
    const name = container.querySelector(".chat-history-name") as HTMLElement;
    expect(name.style.color).toBe("rgb(22, 163, 74)");
  });

  // --- Idle detection ---

  it("shows idle suffix in presence panel for idle remote players", () => {
    const props = {
      ...BASE_SCENE_PROPS,
      remotePlayers: [
        { player_id: "r1", name: "IdleAlice", color: "#e11d48", x: 30, y: 40, direction: "left" as const, walking: false, idle: true },
      ],
    };
    const { container } = render(<HandWorldScene {...props} />);
    const presenceName = container.querySelector(".presence-name");
    expect(presenceName?.textContent).toBe("IdleAlice (idle)");
  });

  it("does not show idle suffix for active remote players", () => {
    const props = {
      ...BASE_SCENE_PROPS,
      remotePlayers: [
        { player_id: "r1", name: "ActiveBob", color: "#2563eb", x: 60, y: 60, direction: "right" as const, walking: false, idle: false },
      ],
    };
    const { container } = render(<HandWorldScene {...props} />);
    const presenceName = container.querySelector(".presence-name");
    expect(presenceName?.textContent).toBe("ActiveBob");
  });

  it("passes isLocalIdle to local player avatar", () => {
    const { container } = render(
      <HandWorldScene {...BASE_SCENE_PROPS} isLocalIdle={true} />
    );
    const indicator = container.querySelector(".human-player .idle-indicator");
    expect(indicator).toBeTruthy();
    expect(indicator?.textContent).toBe("zzz");
  });
});
