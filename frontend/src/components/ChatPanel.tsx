/**
 * ChatPanel — right-side sidebar for multiplayer chat, presence,
 * emote picker, and player customization.
 */
import { useRef, useState, useEffect } from "react";

import {
  CHAT_MAX_LENGTH,
  EMOTE_KEY_BINDINGS,
  EMOTE_MAP,
  PLAYER_COLORS,
} from "../constants";
import type { RemotePlayer, ConnectionStatus } from "../hooks/useMultiplayer";
import { savePlayerColor, savePlayerName } from "../hooks/useMultiplayer";
import type { ChatMessage } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ChatPanelProps = {
  remotePlayers: RemotePlayer[];
  connectionStatus: ConnectionStatus;
  chatHistory: ChatMessage[];
  onSendChat: (message: string) => void;
  onSetTyping: (typing: boolean) => void;
  chatOnCooldown: boolean;
  onTriggerEmote: (key: string) => void;
  playerNameInput: string;
  onPlayerNameChange: (name: string) => void;
  playerColorInput: string;
  onPlayerColorChange: (color: string) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ChatPanel({
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
  collapsed,
  onToggleCollapsed,
}: ChatPanelProps) {
  const [chatInput, setChatInput] = useState("");
  const [emotePickerOpen, setEmotePickerOpen] = useState(false);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const chatHistoryRef = useRef<HTMLDivElement>(null);

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
    <aside className={`card chat-panel-card${collapsed ? " collapsed" : ""}`}>
      <button
        type="button"
        className="sidebar-collapse-btn"
        onClick={onToggleCollapsed}
        aria-label={collapsed ? "Expand chat" : "Collapse chat"}
        aria-expanded={!collapsed}
        title={collapsed ? "Expand chat" : "Collapse chat"}
      >
        {collapsed ? "\u2039" : "\u203A"}
      </button>

      {collapsed ? (
        <div className="sidebar-collapsed-label">Chat</div>
      ) : (
        <>
          <header className="chat-panel-header">
            <h2>Chat</h2>
            <span className={`conn-status-dot conn-status-${connectionStatus}`} aria-label={`Connection: ${connectionStatus}`} />
          </header>

          {/* Player customization */}
          <div className="chat-panel-player">
            <div className="chat-panel-name-row">
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
          </div>

          {/* Presence */}
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

          {/* Chat history */}
          <div
            ref={chatHistoryRef}
            className="chat-history-panel"
            aria-label="Chat history"
          >
            {chatHistory.length === 0 && (
              <div className="chat-empty-hint">No messages yet</div>
            )}
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

          {/* Chat input */}
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

          {/* Emote picker */}
          {connectionStatus === "connected" && (
            <div className="chat-panel-emote-row">
              <button
                type="button"
                className="emote-picker-btn"
                onClick={() => setEmotePickerOpen((v) => !v)}
                aria-label="Toggle emote picker"
                aria-expanded={emotePickerOpen}
              >
                {emotePickerOpen ? "\u2716" : "\u{1F60A}"}
              </button>
              {emotePickerOpen && (
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
            </div>
          )}
        </>
      )}
    </aside>
  );
}
