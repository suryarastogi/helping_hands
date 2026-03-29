import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

import FactoryFloorPanel from "./FactoryFloorPanel";
import type { FactoryFloorPanelProps } from "./FactoryFloorPanel";
import type { RemotePlayer } from "../hooks/useMultiplayer";
import type { ChatMessage, WorldDecoration } from "../types";

const BASE_PROPS: FactoryFloorPanelProps = {
  maxWorkers: 8,
  activeWorkerCount: 0,
  remotePlayers: [],
  connectionStatus: "connected",
  chatHistory: [],
  onSendChat: vi.fn(),
  onSetTyping: vi.fn(),
  chatOnCooldown: false,
  onTriggerEmote: vi.fn(),
  playerNameInput: "Tester",
  onPlayerNameChange: vi.fn(),
  playerColorInput: "#e11d48",
  onPlayerColorChange: vi.fn(),
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

  it("renders player name input with current value", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} playerNameInput="Alice" />);
    const input = container.querySelector(".player-name-input") as HTMLInputElement;
    expect(input).toBeTruthy();
    expect(input.value).toBe("Alice");
  });

  it("calls onPlayerNameChange when name input changes", () => {
    const onNameChange = vi.fn();
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} onPlayerNameChange={onNameChange} />);
    const input = container.querySelector(".player-name-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "NewName" } });
    expect(onNameChange).toHaveBeenCalledWith("NewName");
  });

  it("renders 10 color swatches", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} />);
    expect(container.querySelectorAll(".color-swatch")).toHaveLength(10);
  });

  it("marks selected color swatch", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} playerColorInput="#e11d48" />);
    const swatches = container.querySelectorAll(".color-swatch");
    expect(swatches[0].classList.contains("selected")).toBe(true);
    expect(swatches[1].classList.contains("selected")).toBe(false);
  });

  it("calls onPlayerColorChange when swatch clicked", () => {
    const onColorChange = vi.fn();
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} playerColorInput="" onPlayerColorChange={onColorChange} />);
    const swatches = container.querySelectorAll(".color-swatch");
    fireEvent.click(swatches[2]);
    expect(onColorChange).toHaveBeenCalledWith("#16a34a");
  });

  // --- Presence panel ---

  it("renders presence panel when remote players exist", () => {
    const remotes: RemotePlayer[] = [
      { player_id: "r1", name: "Bob", color: "#2563eb", x: 60, y: 60, direction: "right", walking: true, idle: false, typing: false },
    ];
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} remotePlayers={remotes} />);
    const panel = container.querySelector(".presence-panel");
    expect(panel).toBeTruthy();
    expect(panel?.textContent).toContain("2 Online");
    expect(container.querySelector(".presence-name")?.textContent).toBe("Bob");
  });

  it("hides presence panel when no remote players", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} />);
    expect(container.querySelector(".presence-panel")).toBeNull();
  });

  it("shows idle suffix for idle remote players", () => {
    const remotes: RemotePlayer[] = [
      { player_id: "r1", name: "IdleAlice", color: "#e11d48", x: 30, y: 40, direction: "left", walking: false, idle: true, typing: false },
    ];
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} remotePlayers={remotes} />);
    expect(container.querySelector(".presence-name")?.textContent).toBe("IdleAlice (idle)");
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

  // --- Emote picker ---

  it("shows emote picker button when connected", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} connectionStatus="connected" />);
    expect(container.querySelector(".emote-picker-btn")).toBeTruthy();
  });

  it("hides emote picker button when disconnected", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} connectionStatus="disconnected" />);
    expect(container.querySelector(".emote-picker-btn")).toBeNull();
  });

  it("toggles emote picker panel on button click", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} connectionStatus="connected" />);
    const btn = container.querySelector(".emote-picker-btn")!;
    expect(container.querySelector(".emote-picker-panel")).toBeNull();
    fireEvent.click(btn);
    expect(container.querySelector(".emote-picker-panel")).toBeTruthy();
    fireEvent.click(btn);
    expect(container.querySelector(".emote-picker-panel")).toBeNull();
  });

  it("calls onTriggerEmote and closes panel when emote clicked", () => {
    const onTrigger = vi.fn();
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} onTriggerEmote={onTrigger} />);
    fireEvent.click(container.querySelector(".emote-picker-btn")!);
    fireEvent.click(container.querySelectorAll(".emote-picker-item")[0]);
    expect(onTrigger).toHaveBeenCalledWith("1");
    expect(container.querySelector(".emote-picker-panel")).toBeNull();
  });

  // --- Chat ---

  it("renders chat input when connected", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} connectionStatus="connected" />);
    expect(container.querySelector(".chat-input")).toBeTruthy();
  });

  it("hides chat input when disconnected", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} connectionStatus="disconnected" />);
    expect(container.querySelector(".chat-input")).toBeNull();
  });

  it("calls onSendChat on form submit", () => {
    const onSendChat = vi.fn();
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} onSendChat={onSendChat} />);
    const input = container.querySelector(".chat-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Hello world" } });
    fireEvent.submit(container.querySelector(".chat-input-form")!);
    expect(onSendChat).toHaveBeenCalledWith("Hello world");
    expect(input.value).toBe("");
  });

  it("does not send empty messages", () => {
    const onSendChat = vi.fn();
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} onSendChat={onSendChat} />);
    fireEvent.submit(container.querySelector(".chat-input-form")!);
    expect(onSendChat).not.toHaveBeenCalled();
  });

  it("disables chat input on cooldown", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} chatOnCooldown={true} />);
    const input = container.querySelector(".chat-input") as HTMLInputElement;
    expect(input.disabled).toBe(true);
    expect(input.placeholder).toBe("Wait...");
  });

  it("calls onSetTyping when chat input changes", () => {
    const onSetTyping = vi.fn();
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} onSetTyping={onSetTyping} />);
    fireEvent.change(container.querySelector(".chat-input") as HTMLInputElement, { target: { value: "hi" } });
    expect(onSetTyping).toHaveBeenCalledWith(true);
    onSetTyping.mockClear();
    fireEvent.change(container.querySelector(".chat-input") as HTMLInputElement, { target: { value: "" } });
    expect(onSetTyping).toHaveBeenCalledWith(false);
  });

  it("calls onSetTyping(false) on chat submit", () => {
    const onSetTyping = vi.fn();
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} onSetTyping={onSetTyping} />);
    fireEvent.change(container.querySelector(".chat-input") as HTMLInputElement, { target: { value: "msg" } });
    fireEvent.submit(container.querySelector(".chat-input-form")!);
    expect(onSetTyping).toHaveBeenLastCalledWith(false);
  });

  // --- Chat history ---

  it("renders chat history when messages exist", () => {
    const messages: ChatMessage[] = [
      { id: "m1", playerName: "Alice", playerColor: "#e11d48", text: "Hello!", timestamp: 1000 },
      { id: "m2", playerName: "Bob", playerColor: "#2563eb", text: "Hi!", timestamp: 2000 },
    ];
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} chatHistory={messages} />);
    const panel = container.querySelector(".chat-history-panel");
    expect(panel).toBeTruthy();
    expect(container.querySelectorAll(".chat-history-message")).toHaveLength(2);
  });

  it("hides chat history when no messages", () => {
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} chatHistory={[]} />);
    expect(container.querySelector(".chat-history-panel")).toBeNull();
  });

  it("renders system messages with system class", () => {
    const messages: ChatMessage[] = [
      { id: "sys1", playerName: "System", playerColor: "#6b7280", text: "Player joined", timestamp: 1000, isSystem: true },
    ];
    const { container } = render(<FactoryFloorPanel {...BASE_PROPS} chatHistory={messages} />);
    expect(container.querySelector(".chat-history-system")).toBeTruthy();
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
