/**
 * FactoryFloorPanel — the left-side HUD panel in Hand World.
 *
 * Contains station/worker counts, player name & color customization,
 * connected-player presence list, connection status indicator, emote picker,
 * chat input with history, and the shared decoration toolbar.
 */
import { useRef, useState, useEffect } from "react";

import {
  CHAT_MAX_LENGTH,
  DECORATION_EMOJIS,
  EMOTE_KEY_BINDINGS,
  EMOTE_MAP,
  MAX_DECORATIONS,
  PLAYER_COLORS,
} from "../constants";
import type { RemotePlayer, ConnectionStatus } from "../hooks/useMultiplayer";
import { savePlayerColor, savePlayerName } from "../hooks/useMultiplayer";
import type { ChatMessage, WorldDecoration } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type FactoryFloorPanelProps = {
  maxWorkers: number;
  activeWorkerCount: number;
  // -- Multiplayer --
  remotePlayers: RemotePlayer[];
  connectionStatus: ConnectionStatus;
  chatHistory: ChatMessage[];
  onSendChat: (message: string) => void;
  onSetTyping: (typing: boolean) => void;
  chatOnCooldown: boolean;
  onTriggerEmote: (key: string) => void;
  // -- Player customization --
  playerNameInput: string;
  onPlayerNameChange: (name: string) => void;
  playerColorInput: string;
  onPlayerColorChange: (color: string) => void;
  // -- Decorations --
  decorations: WorldDecoration[];
  onClearDecorations: () => void;
  /** Currently selected decoration emoji (managed by parent for deco-placing class). */
  selectedDecoEmoji: string | null;
  onSelectedDecoEmojiChange: (emoji: string | null) => void;
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function FactoryFloorPanel({
  maxWorkers,
  activeWorkerCount,
  remotePlayers,
  connectionStatus,
  chatHistory,
  onSendChat,
  onSetTyping,
  chatOnCooldown,
  onTriggerEmote,
  playerNameInput,
  onPlayerNameChange,
  playerColorInput,
  onPlayerColorChange,
  decorations,
  onClearDecorations,
  selectedDecoEmoji,
  onSelectedDecoEmojiChange,
}: FactoryFloorPanelProps) {
  const [chatInput, setChatInput] = useState("");
  const [emotePickerOpen, setEmotePickerOpen] = useState(false);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const chatHistoryRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat history to bottom when new messages arrive.
  useEffect(() => {
    const el = chatHistoryRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [chatHistory.length]);

  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = chatInput.trim();
    if (!text || chatOnCooldown) return;
    onSendChat(text);
    setChatInput("");
    onSetTyping(false);
    chatInputRef.current?.blur();
  };

  return (
    <div className="zen-status-summary">
      <div className="status-summary-header">Factory Floor</div>
      <div className="status-summary-stat">
        <span className="stat-icon">&#128187;</span>
        <span>{maxWorkers} Stations</span>
      </div>
      <div className="status-summary-stat">
        <span className="stat-icon">&#129302;</span>
        <span>{activeWorkerCount} Active</span>
      </div>
      <div className="status-summary-stat player-name-row">
        <span className="stat-icon">&#128100;</span>
        <input
          type="text"
          className="player-name-input"
          value={playerNameInput}
          onChange={(e) => {
            onPlayerNameChange(e.target.value);
            savePlayerName(e.target.value);
          }}
          placeholder="Your name"
          maxLength={24}
          aria-label="Player name"
        />
      </div>
      <div className="color-picker-row" aria-label="Player color">
        {PLAYER_COLORS.map((c) => (
          <button
            key={c}
            type="button"
            className={`color-swatch${playerColorInput === c ? " selected" : ""}`}
            style={{ backgroundColor: c }}
            onClick={() => {
              onPlayerColorChange(c);
              savePlayerColor(c);
            }}
            aria-label={`Select color ${c}`}
            aria-pressed={playerColorInput === c}
          />
        ))}
      </div>
      {remotePlayers.length > 0 && (
        <div className="presence-panel" aria-label="Connected players">
          <div className="presence-header">
            <span className="stat-icon">&#128101;</span>
            <span>{remotePlayers.length + 1} Online</span>
          </div>
          <ul className="presence-list">
            {remotePlayers.map((rp) => (
              <li key={rp.player_id} className="presence-item">
                <span
                  className="presence-dot"
                  style={{ backgroundColor: rp.color }}
                />
                <span className="presence-name">
                  {rp.name}{rp.idle ? " (idle)" : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="status-summary-hint">
        <span className={`conn-status-dot conn-status-${connectionStatus}`} aria-label={`Connection: ${connectionStatus}`} />
        {connectionStatus === "connected"
          ? "Multiplayer active \u00b7 Arrow keys: walk"
          : connectionStatus === "connecting"
            ? "Connecting\u2026"
            : connectionStatus === "failed"
              ? "Connection failed"
              : "Disconnected \u00b7 Arrow keys: walk"}
        {connectionStatus === "connected" && (
          <button
            type="button"
            className="emote-picker-btn"
            onClick={() => setEmotePickerOpen((v) => !v)}
            aria-label="Toggle emote picker"
            aria-expanded={emotePickerOpen}
          >
            {emotePickerOpen ? "\u2716" : "\u{1F60A}"}
          </button>
        )}
      </div>
      {emotePickerOpen && connectionStatus === "connected" && (
        <div className="emote-picker-panel" role="group" aria-label="Emote picker">
          {Object.entries(EMOTE_KEY_BINDINGS).map(([key, emoteName]) => (
            <button
              key={key}
              type="button"
              className="emote-picker-item"
              onClick={() => {
                onTriggerEmote(key);
                setEmotePickerOpen(false);
              }}
              aria-label={`Send ${emoteName} emote`}
            >
              <span className="emote-picker-emoji">{EMOTE_MAP[emoteName]}</span>
              <span className="emote-picker-label">{emoteName}</span>
              <kbd className="emote-picker-key">{key}</kbd>
            </button>
          ))}
        </div>
      )}
      {connectionStatus === "connected" && (
        <form className="chat-input-form" onSubmit={handleChatSubmit}>
          <input
            ref={chatInputRef}
            type="text"
            className="chat-input"
            value={chatInput}
            onChange={(e) => {
              setChatInput(e.target.value);
              onSetTyping(e.target.value.length > 0);
            }}
            onFocus={() => { if (chatInput.length > 0) onSetTyping(true); }}
            onBlur={() => onSetTyping(false)}
            placeholder={chatOnCooldown ? "Wait..." : "Press Enter to chat..."}
            maxLength={CHAT_MAX_LENGTH}
            disabled={chatOnCooldown}
            aria-label="Chat message"
          />
        </form>
      )}
      {chatHistory.length > 0 && (
        <div
          ref={chatHistoryRef}
          className="chat-history-panel"
          aria-label="Chat history"
        >
          {chatHistory.map((msg) => (
            <div key={msg.id} className={`chat-history-message${msg.isSystem ? " chat-history-system" : ""}`}>
              <span
                className="chat-history-name"
                style={{ color: msg.playerColor }}
              >
                {msg.playerName}
              </span>
              <span className="chat-history-text">{msg.text}</span>
            </div>
          ))}
        </div>
      )}
      {connectionStatus === "connected" && (
        <div className="decoration-toolbar" aria-label="Decoration toolbar">
          <div className="decoration-toolbar-header">
            <span>Decorations ({decorations.length}/{MAX_DECORATIONS})</span>
            {decorations.length > 0 && (
              <button
                type="button"
                className="decoration-clear-btn"
                onClick={onClearDecorations}
                aria-label="Clear all decorations"
              >
                Clear
              </button>
            )}
          </div>
          <div className="decoration-palette" role="group" aria-label="Decoration emoji palette">
            {DECORATION_EMOJIS.map((emoji) => (
              <button
                key={emoji}
                type="button"
                className={`decoration-emoji-btn${selectedDecoEmoji === emoji ? " selected" : ""}`}
                onClick={() => onSelectedDecoEmojiChange(selectedDecoEmoji === emoji ? null : emoji)}
                disabled={decorations.length >= MAX_DECORATIONS}
                aria-label={`Select ${emoji} decoration`}
                aria-pressed={selectedDecoEmoji === emoji}
              >
                {emoji}
              </button>
            ))}
          </div>
          {selectedDecoEmoji && (
            <div className="decoration-hint">Double-click the scene to place {selectedDecoEmoji}</div>
          )}
        </div>
      )}
    </div>
  );
}
