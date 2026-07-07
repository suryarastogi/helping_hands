/**
 * MultiplayerGrillLobby — session list + inline "Create Session" form.
 *
 * Shows at most 50 active sessions sorted by last activity.  The top card
 * is auto-highlighted so the UX matches the original framing of "open the
 * latest active grill" while allowing multiple concurrent sessions.
 */
import { useState } from "react";

import type { MGrillCreateForm, MGrillSessionSummary } from "../types";
import type { MGrillLobbyState } from "../hooks/useMultiplayerGrill";

type Props = {
  lobby: MGrillLobbyState;
  showCreate: boolean;
  onToggleCreate: () => void;
  onCreate: (form: MGrillCreateForm) => Promise<void>;
  onJoin: (summary: MGrillSessionSummary) => void;
  onClose: () => void;
  isCreating: boolean;
  error: string | null;
  initialCreateForm?: Partial<MGrillCreateForm>;
  serverHasGithubToken?: boolean;
};

function formatRelative(ts: number): string {
  if (!ts) return "—";
  const ageS = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (ageS < 10) return "just now";
  if (ageS < 60) return `${ageS}s ago`;
  if (ageS < 3600) return `${Math.floor(ageS / 60)}m ago`;
  return `${Math.floor(ageS / 3600)}h ago`;
}

export default function MultiplayerGrillLobby({
  lobby,
  showCreate,
  onToggleCreate,
  onCreate,
  onJoin,
  onClose,
  isCreating,
  error,
  initialCreateForm,
  serverHasGithubToken,
}: Props) {
  const [form, setForm] = useState<MGrillCreateForm>({
    repo_path: initialCreateForm?.repo_path ?? "",
    prompt: initialCreateForm?.prompt ?? "",
    model: initialCreateForm?.model ?? "",
    backend: initialCreateForm?.backend ?? "claudecodecli",
    reference_repos: initialCreateForm?.reference_repos ?? "",
  });

  const canSubmit = form.repo_path.trim().length > 0 && form.prompt.trim().length > 0;

  return (
    <div className="card mgrill-lobby-card">
      <header className="mgrill-header">
        <h1>Multiplayer Grill Me</h1>
        <button
          type="button"
          className="mgrill-close-btn"
          onClick={onClose}
          aria-label="Close multiplayer grill"
        >
          &times;
        </button>
      </header>

      <div className="mgrill-lobby-body">
        <div className="mgrill-lobby-list-header">
          <h2>Active sessions</h2>
          <button
            type="button"
            className="mgrill-create-toggle"
            onClick={onToggleCreate}
            aria-expanded={showCreate}
          >
            {showCreate ? "Cancel" : "New session"}
          </button>
        </div>

        {showCreate && (
          <form
            className="mgrill-create-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (!canSubmit) return;
              void onCreate(form);
            }}
          >
            <label>
              <span>Repo path or owner/repo</span>
              <input
                type="text"
                value={form.repo_path}
                onChange={(e) => setForm((f) => ({ ...f, repo_path: e.target.value }))}
                placeholder="owner/repo"
                required
              />
            </label>
            <label>
              <span>Plan / task</span>
              <textarea
                value={form.prompt}
                onChange={(e) => setForm((f) => ({ ...f, prompt: e.target.value }))}
                placeholder="Describe the plan you want grilled..."
                rows={4}
                required
              />
            </label>
            <label>
              <span>Model (optional)</span>
              <input
                type="text"
                value={form.model}
                onChange={(e) => setForm((f) => ({ ...f, model: e.target.value }))}
                placeholder="default for backend"
              />
            </label>
            <label>
              <span>Backend</span>
              <select
                value={form.backend}
                onChange={(e) => setForm((f) => ({ ...f, backend: e.target.value }))}
              >
                <option value="claudecodecli">Claude Code CLI</option>
                <option value="codexcli">Codex CLI</option>
              </select>
            </label>
            <label>
              <span>Reference repos (comma-separated, optional)</span>
              <input
                type="text"
                value={form.reference_repos}
                onChange={(e) =>
                  setForm((f) => ({ ...f, reference_repos: e.target.value }))
                }
                placeholder="owner/ref-one, owner/ref-two"
              />
            </label>
            {!serverHasGithubToken && (
              <p className="mgrill-hint">
                Your GitHub token (from session storage) will be used for the creator's
                repo access and as your identity for creator-only actions.
              </p>
            )}
            {error && <p className="mgrill-error">{error}</p>}
            <div className="mgrill-create-actions">
              <button type="submit" disabled={!canSubmit || isCreating}>
                {isCreating ? "Creating…" : "Create session"}
              </button>
            </div>
          </form>
        )}

        {lobby.error && !showCreate && (
          <p className="mgrill-error">Couldn't load sessions: {lobby.error}</p>
        )}

        {lobby.sessions.length === 0 && !lobby.isLoading && !showCreate && (
          <div className="mgrill-empty">
            <p>No active grill sessions.</p>
            <button type="button" onClick={onToggleCreate}>
              Start one
            </button>
          </div>
        )}

        <ul className="mgrill-session-list">
          {lobby.sessions.map((s, idx) => (
            <li key={s.session_id} className={`mgrill-session-card${idx === 0 ? " top" : ""}`}>
              <div className="mgrill-session-meta">
                <span className={`mgrill-session-status status-${s.status}`}>
                  {s.status}
                </span>
                <span className="mgrill-session-turn">turn {s.turn_count}</span>
                {s.has_final_plan && (
                  <span className="mgrill-session-flag">has plan</span>
                )}
              </div>
              <h3 className="mgrill-session-title">{s.creator_name}'s session</h3>
              <p className="mgrill-session-repo">{s.repo_path}</p>
              <p className="mgrill-session-prompt" title={s.prompt}>
                {s.prompt.slice(0, 140)}
                {s.prompt.length > 140 ? "…" : ""}
              </p>
              <div className="mgrill-session-actions">
                <span className="mgrill-session-age">
                  active {formatRelative(s.last_activity_ts)}
                </span>
                {s.status !== "completed" && s.status !== "submitted" ? (
                  <button type="button" onClick={() => onJoin(s)}>
                    Join
                  </button>
                ) : (
                  <span className="mgrill-session-done">
                    {s.status === "submitted" ? "Submitted" : "Completed"}
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
