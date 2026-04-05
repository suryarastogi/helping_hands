import { render, screen, fireEvent, within, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";

import ChatPanel from "./ChatPanel";
import type { ChatPanelProps } from "./ChatPanel";
import { PLAYER_COLORS, EMOTE_KEY_BINDINGS, EMOTE_MAP } from "../constants";
import type { ChatMessage } from "../types";

// ---------------------------------------------------------------------------
// Mock savePlayerName / savePlayerColor — they write to localStorage
// ---------------------------------------------------------------------------
vi.mock("../hooks/useMultiplayer", () => ({
  savePlayerName: vi.fn(),
  savePlayerColor: vi.fn(),
}));

import { savePlayerName, savePlayerColor } from "../hooks/useMultiplayer";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeMsg(overrides: Partial<ChatMessage> & { id: string }): ChatMessage {
  return {
    playerName: "Alice",
    playerColor: "#e11d48",
    text: "hello",
    timestamp: Date.now(),
    ...overrides,
  };
}

function makeProps(overrides: Partial<ChatPanelProps> = {}): ChatPanelProps {
  return {
    remotePlayers: [],
    connectionStatus: "connected",
    chatHistory: [],
    onSendChat: vi.fn(),
    onSetTyping: vi.fn(),
    chatOnCooldown: false,
    onTriggerEmote: vi.fn(),
    playerNameInput: "TestUser",
    onPlayerNameChange: vi.fn(),
    playerColorInput: PLAYER_COLORS[0],
    onPlayerColorChange: vi.fn(),
    collapsed: false,
    onToggleCollapsed: vi.fn(),
    ...overrides,
  };
}

function renderPanel(overrides: Partial<ChatPanelProps> = {}) {
  const props = makeProps(overrides);
  const result = render(<ChatPanel {...props} />);
  return { ...result, props };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ChatPanel", () => {
  // ---- Collapsed / Expanded ----

  describe("collapsed state", () => {
    it("renders collapsed label when collapsed", () => {
      renderPanel({ collapsed: true });
      expect(screen.getByText("Chat")).toBeInTheDocument();
    });

    it("shows expand button with correct aria-label when collapsed", () => {
      renderPanel({ collapsed: true });
      const btn = screen.getByRole("button", { name: "Expand chat" });
      expect(btn).toBeInTheDocument();
      expect(btn.getAttribute("aria-expanded")).toBe("false");
    });

    it("does not render chat header when collapsed", () => {
      renderPanel({ collapsed: true });
      expect(screen.queryByRole("heading", { name: "Chat" })).not.toBeInTheDocument();
    });

    it("shows collapse button with correct aria when expanded", () => {
      renderPanel({ collapsed: false });
      const btn = screen.getByRole("button", { name: "Collapse chat" });
      expect(btn).toBeInTheDocument();
      expect(btn.getAttribute("aria-expanded")).toBe("true");
    });

    it("calls onToggleCollapsed when toggle button clicked", () => {
      const { props } = renderPanel({ collapsed: false });
      fireEvent.click(screen.getByRole("button", { name: "Collapse chat" }));
      expect(props.onToggleCollapsed).toHaveBeenCalledTimes(1);
    });
  });

  // ---- Header ----

  describe("header", () => {
    it("renders Chat heading when expanded", () => {
      renderPanel();
      expect(screen.getByRole("heading", { name: "Chat" })).toBeInTheDocument();
    });

    it("shows connection status dot", () => {
      renderPanel({ connectionStatus: "connecting" });
      expect(screen.getByLabelText("Connection: connecting")).toBeInTheDocument();
    });
  });

  // ---- Player customization ----

  describe("player customization", () => {
    it("renders player name input with current value", () => {
      renderPanel({ playerNameInput: "Bob" });
      const input = screen.getByLabelText("Player name") as HTMLInputElement;
      expect(input.value).toBe("Bob");
    });

    it("calls onPlayerNameChange and savePlayerName on name input", () => {
      const { props } = renderPanel();
      fireEvent.change(screen.getByLabelText("Player name"), {
        target: { value: "NewName" },
      });
      expect(props.onPlayerNameChange).toHaveBeenCalledWith("NewName");
      expect(savePlayerName).toHaveBeenCalledWith("NewName");
    });

    it("renders color swatches for all PLAYER_COLORS", () => {
      renderPanel();
      for (const c of PLAYER_COLORS) {
        expect(screen.getByLabelText(`Select color ${c}`)).toBeInTheDocument();
      }
    });

    it("marks selected color with aria-pressed=true", () => {
      renderPanel({ playerColorInput: PLAYER_COLORS[2] });
      const btn = screen.getByLabelText(`Select color ${PLAYER_COLORS[2]}`);
      expect(btn.getAttribute("aria-pressed")).toBe("true");
      const other = screen.getByLabelText(`Select color ${PLAYER_COLORS[0]}`);
      expect(other.getAttribute("aria-pressed")).toBe("false");
    });

    it("calls onPlayerColorChange and savePlayerColor on color click", () => {
      const { props } = renderPanel();
      fireEvent.click(screen.getByLabelText(`Select color ${PLAYER_COLORS[3]}`));
      expect(props.onPlayerColorChange).toHaveBeenCalledWith(PLAYER_COLORS[3]);
      expect(savePlayerColor).toHaveBeenCalledWith(PLAYER_COLORS[3]);
    });
  });

  // ---- Presence panel ----

  describe("presence panel", () => {
    it("does not render presence when no remote players", () => {
      renderPanel({ remotePlayers: [] });
      expect(screen.queryByLabelText("Connected players")).not.toBeInTheDocument();
    });

    it("renders presence panel with player count (+1 for self)", () => {
      const players = [
        { player_id: "p1", name: "Alice", color: "#e11d48", x: 0, y: 0, direction: "right" as const, walking: false, idle: false, typing: false, emote: null, emoteExpiry: 0 },
        { player_id: "p2", name: "Bob", color: "#2563eb", x: 0, y: 0, direction: "left" as const, walking: false, idle: true, typing: false, emote: null, emoteExpiry: 0 },
      ];
      renderPanel({ remotePlayers: players });
      expect(screen.getByLabelText("Connected players")).toBeInTheDocument();
      expect(screen.getByText("3 Online")).toBeInTheDocument();
    });

    it("shows idle indicator for idle players", () => {
      const players = [
        { player_id: "p1", name: "Eve", color: "#16a34a", x: 0, y: 0, direction: "right" as const, walking: false, idle: true, typing: false, emote: null, emoteExpiry: 0 },
      ];
      renderPanel({ remotePlayers: players });
      expect(screen.getByText(/Eve.*\(idle\)/)).toBeInTheDocument();
    });
  });

  // ---- Chat history ----

  describe("chat history", () => {
    it("shows empty hint when no messages", () => {
      renderPanel({ chatHistory: [] });
      expect(screen.getByText("No messages yet")).toBeInTheDocument();
    });

    it("renders chat messages with player name and text", () => {
      const msgs = [
        makeMsg({ id: "m1", playerName: "Alice", text: "hello world" }),
        makeMsg({ id: "m2", playerName: "Bob", playerColor: "#2563eb", text: "hi there" }),
      ];
      renderPanel({ chatHistory: msgs });
      expect(screen.getByText("Alice")).toBeInTheDocument();
      expect(screen.getByText("hello world")).toBeInTheDocument();
      expect(screen.getByText("Bob")).toBeInTheDocument();
      expect(screen.getByText("hi there")).toBeInTheDocument();
    });

    it("applies system message class for system messages", () => {
      const msgs = [makeMsg({ id: "s1", isSystem: true, text: "joined" })];
      const { container } = renderPanel({ chatHistory: msgs });
      const msgEl = container.querySelector(".chat-history-system");
      expect(msgEl).toBeTruthy();
    });

    it("does not show empty hint when messages exist", () => {
      const msgs = [makeMsg({ id: "m1" })];
      renderPanel({ chatHistory: msgs });
      expect(screen.queryByText("No messages yet")).not.toBeInTheDocument();
    });
  });

  // ---- Chat input ----

  describe("chat input", () => {
    it("renders chat input when connected", () => {
      renderPanel({ connectionStatus: "connected" });
      expect(screen.getByLabelText("Chat message")).toBeInTheDocument();
    });

    it("does not render chat input when disconnected", () => {
      renderPanel({ connectionStatus: "disconnected" });
      expect(screen.queryByLabelText("Chat message")).not.toBeInTheDocument();
    });

    it("shows cooldown placeholder when on cooldown", () => {
      renderPanel({ chatOnCooldown: true });
      const input = screen.getByLabelText("Chat message") as HTMLInputElement;
      expect(input.placeholder).toBe("Wait...");
      expect(input.disabled).toBe(true);
    });

    it("shows normal placeholder when not on cooldown", () => {
      renderPanel({ chatOnCooldown: false });
      const input = screen.getByLabelText("Chat message") as HTMLInputElement;
      expect(input.placeholder).toBe("Press Enter to chat...");
      expect(input.disabled).toBe(false);
    });

    it("calls onSetTyping(true) when typing non-empty text", () => {
      const { props } = renderPanel();
      fireEvent.change(screen.getByLabelText("Chat message"), {
        target: { value: "hi" },
      });
      expect(props.onSetTyping).toHaveBeenCalledWith(true);
    });

    it("calls onSetTyping(false) when clearing input", () => {
      const { props } = renderPanel();
      const input = screen.getByLabelText("Chat message");
      // Type something first so clearing is a real change
      fireEvent.change(input, { target: { value: "hi" } });
      vi.clearAllMocks();
      fireEvent.change(input, { target: { value: "" } });
      expect(props.onSetTyping).toHaveBeenCalledWith(false);
    });

    it("calls onSetTyping(true) on focus when input has text", () => {
      const { props } = renderPanel();
      const input = screen.getByLabelText("Chat message");
      // First type something
      fireEvent.change(input, { target: { value: "hello" } });
      vi.clearAllMocks();
      fireEvent.focus(input);
      expect(props.onSetTyping).toHaveBeenCalledWith(true);
    });

    it("calls onSetTyping(false) on blur", () => {
      const { props } = renderPanel();
      const input = screen.getByLabelText("Chat message");
      fireEvent.blur(input);
      expect(props.onSetTyping).toHaveBeenCalledWith(false);
    });
  });

  // ---- Chat submission ----

  describe("chat submission", () => {
    it("sends trimmed message on form submit", () => {
      const { props } = renderPanel();
      const input = screen.getByLabelText("Chat message");
      fireEvent.change(input, { target: { value: "  hello  " } });
      fireEvent.submit(input.closest("form")!);
      expect(props.onSendChat).toHaveBeenCalledWith("hello");
    });

    it("clears input after sending", () => {
      renderPanel();
      const input = screen.getByLabelText("Chat message") as HTMLInputElement;
      fireEvent.change(input, { target: { value: "test" } });
      fireEvent.submit(input.closest("form")!);
      expect(input.value).toBe("");
    });

    it("calls onSetTyping(false) after sending", () => {
      const { props } = renderPanel();
      const input = screen.getByLabelText("Chat message");
      fireEvent.change(input, { target: { value: "hi" } });
      vi.clearAllMocks();
      fireEvent.submit(input.closest("form")!);
      expect(props.onSetTyping).toHaveBeenCalledWith(false);
    });

    it("does not send empty message", () => {
      const { props } = renderPanel();
      const input = screen.getByLabelText("Chat message");
      fireEvent.submit(input.closest("form")!);
      expect(props.onSendChat).not.toHaveBeenCalled();
    });

    it("does not send whitespace-only message", () => {
      const { props } = renderPanel();
      const input = screen.getByLabelText("Chat message");
      fireEvent.change(input, { target: { value: "   " } });
      fireEvent.submit(input.closest("form")!);
      expect(props.onSendChat).not.toHaveBeenCalled();
    });

    it("does not send when on cooldown", () => {
      const { props } = renderPanel({ chatOnCooldown: true });
      const input = screen.getByLabelText("Chat message");
      fireEvent.change(input, { target: { value: "hi" } });
      fireEvent.submit(input.closest("form")!);
      expect(props.onSendChat).not.toHaveBeenCalled();
    });
  });

  // ---- Emote picker ----

  describe("emote picker", () => {
    it("renders emote toggle button when connected", () => {
      renderPanel({ connectionStatus: "connected" });
      expect(screen.getByLabelText("Toggle emote picker")).toBeInTheDocument();
    });

    it("does not render emote toggle when disconnected", () => {
      renderPanel({ connectionStatus: "disconnected" });
      expect(screen.queryByLabelText("Toggle emote picker")).not.toBeInTheDocument();
    });

    it("opens emote picker on toggle click", () => {
      renderPanel();
      fireEvent.click(screen.getByLabelText("Toggle emote picker"));
      expect(screen.getByRole("group", { name: "Emote picker" })).toBeInTheDocument();
    });

    it("renders all emote options", () => {
      renderPanel();
      fireEvent.click(screen.getByLabelText("Toggle emote picker"));
      for (const [, emoteName] of Object.entries(EMOTE_KEY_BINDINGS)) {
        expect(screen.getByLabelText(`Send ${emoteName} emote`)).toBeInTheDocument();
      }
    });

    it("shows emoji and label for each emote", () => {
      renderPanel();
      fireEvent.click(screen.getByLabelText("Toggle emote picker"));
      for (const [, emoteName] of Object.entries(EMOTE_KEY_BINDINGS)) {
        expect(screen.getByText(EMOTE_MAP[emoteName])).toBeInTheDocument();
        expect(screen.getByText(emoteName)).toBeInTheDocument();
      }
    });

    it("calls onTriggerEmote and closes picker on emote click", () => {
      const { props } = renderPanel();
      fireEvent.click(screen.getByLabelText("Toggle emote picker"));
      const firstKey = Object.keys(EMOTE_KEY_BINDINGS)[0];
      const firstName = EMOTE_KEY_BINDINGS[firstKey];
      fireEvent.click(screen.getByLabelText(`Send ${firstName} emote`));
      expect(props.onTriggerEmote).toHaveBeenCalledWith(firstKey);
      // Picker should close
      expect(screen.queryByRole("group", { name: "Emote picker" })).not.toBeInTheDocument();
    });

    it("closes emote picker on second toggle click", () => {
      renderPanel();
      const toggle = screen.getByLabelText("Toggle emote picker");
      fireEvent.click(toggle);
      expect(screen.getByRole("group", { name: "Emote picker" })).toBeInTheDocument();
      fireEvent.click(toggle);
      expect(screen.queryByRole("group", { name: "Emote picker" })).not.toBeInTheDocument();
    });

    it("shows aria-expanded correctly on toggle", () => {
      renderPanel();
      const toggle = screen.getByLabelText("Toggle emote picker");
      expect(toggle.getAttribute("aria-expanded")).toBe("false");
      fireEvent.click(toggle);
      expect(toggle.getAttribute("aria-expanded")).toBe("true");
    });
  });
});
