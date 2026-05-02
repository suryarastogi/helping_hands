import { useState } from "react";

type Props = {
  token: string;
  onTokenChange: (token: string) => void;
  serverHasGithubToken: boolean;
};

export default function TokenBar({ token, onTokenChange, serverHasGithubToken }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  if (serverHasGithubToken && !token) return null;

  const hasToken = Boolean(token.trim());

  const handleStartEdit = () => {
    setDraft(token);
    setEditing(true);
  };

  const handleSave = () => {
    onTokenChange(draft.trim());
    setEditing(false);
  };

  const handleCancel = () => {
    setEditing(false);
  };

  const handleClear = () => {
    onTokenChange("");
  };

  const maskedToken = token.length > 8
    ? `${token.slice(0, 4)}${"•".repeat(8)}${token.slice(-4)}`
    : "•".repeat(token.length);

  if (editing) {
    return (
      <div className="token-bar">
        <span className="token-bar-icon">🔑</span>
        <input
          className="token-bar-input"
          type="password"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSave();
            if (e.key === "Escape") handleCancel();
          }}
          placeholder="ghp_..."
          autoFocus
        />
        <button type="button" className="token-bar-btn" onClick={handleSave}>Save</button>
        <button type="button" className="token-bar-btn" onClick={handleCancel}>Cancel</button>
      </div>
    );
  }

  if (!hasToken) {
    return (
      <div className="token-bar token-bar-warn">
        <span className="token-bar-icon">⚠</span>
        <span className="token-bar-label">No GitHub token set</span>
        <button type="button" className="token-bar-btn" onClick={handleStartEdit}>Set Token</button>
      </div>
    );
  }

  return (
    <div className="token-bar">
      <span className="token-bar-icon">🔑</span>
      <span className="token-bar-masked">{maskedToken}</span>
      <button type="button" className="token-bar-btn" onClick={handleStartEdit}>Edit</button>
      <button type="button" className="token-bar-btn" onClick={handleClear}>Clear</button>
    </div>
  );
}
