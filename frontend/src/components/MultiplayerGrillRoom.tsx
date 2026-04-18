/**
 * MultiplayerGrillRoom — in-session UI for a multiplayer grill.
 *
 * Layout:
 *  - Header: session meta + creator/status badges + close button
 *  - Transcript: messages from worker + bundled user turns + system hints
 *  - Pending batch panel: each participant's queued message, inline compose
 *  - Bottom action bar: Send to AI (any token-holder) / vote widget /
 *    Submit + Keep Grilling (creator-only) depending on phase
 *
 * Uses the ``useMultiplayerGrill`` actions for every backend call so this
 * component stays focused on rendering + local input state.
 */
import { useEffect, useMemo, useState } from "react";

import type { MGrillSessionActions } from "../hooks/useMultiplayerGrill";
import { loadGithubToken } from "../App.utils";

type Props = {
  actions: MGrillSessionActions;
  playerId: string;
  playerName: string;
  /** When true, the server has its own GITHUB_TOKEN — token-gated UI is
   *  unlocked for everyone (the server token satisfies auth). */
  serverHasGithubToken?: boolean;
  onClose: () => void;
  onLeave: () => void;
};

export default function MultiplayerGrillRoom({
  actions,
  playerId,
  playerName,
  serverHasGithubToken = false,
  onClose,
  onLeave,
}: Props) {
  const { state, live, sessionId } = actions;
  const [draft, setDraft] = useState("");
  const [showOverrideConfirm, setShowOverrideConfirm] = useState(false);
  const [submitBusy, setSubmitBusy] = useState(false);
  const [claimBusy, setClaimBusy] = useState(false);
  const [nowTick, setNowTick] = useState(Date.now());
  // Effective auth: the server-wide token (when configured) unlocks chat
  // + vote + submit for all clients; otherwise participants need their own.
  const hasToken = serverHasGithubToken || Boolean(loadGithubToken());

  // Tick every second so the creator-absent timer updates live.
  useEffect(() => {
    const h = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => window.clearInterval(h);
  }, []);

  const myVote = live.votes[playerId] ?? null;
  const pending = live.pending;
  const messages = live.messages;
  const isThinking = state?.status === "thinking";
  const hasFinalPlan = Boolean(live.finalPlan);
  const isCreator = Boolean(state?.is_creator);
  const canActAsCreator = Boolean(state?.can_act_as_creator);
  const creatorAbsentS = state
    ? Math.max(0, Math.floor(nowTick / 1000 - state.creator_last_seen_ts))
    : 0;
  // When the server has a global token, creator identity is server-owned
  // and handoff is moot — every authenticated caller is already creator.
  const canClaimCreator =
    !serverHasGithubToken && !canActAsCreator && creatorAbsentS > 60 && hasToken;

  const voteTally = useMemo(() => {
    const values = Object.values(live.votes);
    return {
      up: values.filter((v) => v === "up").length,
      down: values.filter((v) => v === "down").length,
      total: values.length,
    };
  }, [live.votes]);

  const handleAddPending = async () => {
    const trimmed = draft.trim();
    if (!trimmed || !hasToken) return;
    setDraft("");
    await actions.addPending(trimmed, playerId, playerName);
  };

  const handleSend = async () => {
    if (pending.length === 0 || !hasToken) return;
    await actions.sendToAi();
  };

  const handleSubmit = async (override: boolean) => {
    setSubmitBusy(true);
    try {
      const result = await actions.submitPlan({ override });
      if (!result.ok) {
        if (result.status === 409) {
          setShowOverrideConfirm(true);
        }
      } else {
        setShowOverrideConfirm(false);
      }
    } finally {
      setSubmitBusy(false);
    }
  };

  const handleClaim = async () => {
    setClaimBusy(true);
    try {
      await actions.claimCreator(playerId, playerName);
    } finally {
      setClaimBusy(false);
    }
  };

  return (
    <div className="card mgrill-room-card">
      <header className="mgrill-header">
        <div className="mgrill-room-title">
          <h1>Multiplayer Grill</h1>
          <div className="mgrill-room-sub">
            <span className={`mgrill-session-status status-${state?.status ?? "loading"}`}>
              {state?.status ?? "loading"}
            </span>
            <span className="mgrill-room-creator">
              Creator: {state?.creator_name ?? "?"}
              {isCreator && <span className="mgrill-you-badge"> (you)</span>}
            </span>
            <span className="mgrill-room-turn">turn {state?.turn_count ?? 0}</span>
          </div>
          <p className="mgrill-room-repo">{state?.repo_path}</p>
        </div>
        <div className="mgrill-room-header-actions">
          <button type="button" className="mgrill-leave-btn" onClick={onLeave}>
            Leave
          </button>
          <button
            type="button"
            className="mgrill-close-btn"
            onClick={onClose}
            aria-label="Close"
          >
            &times;
          </button>
        </div>
      </header>

      {canClaimCreator && (
        <div className="mgrill-banner mgrill-banner-claim">
          <span>
            Creator has been absent for {creatorAbsentS}s. You can take over Submit/Keep Grilling.
          </span>
          <button type="button" onClick={handleClaim} disabled={claimBusy}>
            {claimBusy ? "Claiming…" : "Claim creator"}
          </button>
        </div>
      )}

      {!hasToken && (
        <div className="mgrill-banner mgrill-banner-readonly">
          Read-only: add a GitHub token in the submission form to participate
          in chat and voting.
        </div>
      )}

      <div className="mgrill-transcript" aria-live="polite">
        {messages.length === 0 && <p className="mgrill-loading">Loading…</p>}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`mgrill-msg mgrill-msg-${m.role} mgrill-msg-type-${m.type}`}
          >
            <div className="mgrill-msg-head">
              <span className="mgrill-msg-author">
                {m.author_name ?? (m.role === "assistant" ? "Interviewer" : m.role)}
              </span>
              <span className="mgrill-msg-ts">
                {new Date(m.timestamp * 1000).toLocaleTimeString()}
              </span>
            </div>
            <div className="mgrill-msg-body">{m.content}</div>
          </div>
        ))}
        {isThinking && (
          <div className="mgrill-thinking">Interviewer is thinking…</div>
        )}
      </div>

      {hasFinalPlan && (
        <div className="mgrill-vote-panel">
          <h3>Final plan voting</h3>
          <p className="mgrill-vote-hint">
            Votes are per tab, not per person — consensus signal only. The
            creator is the sole decider.
          </p>
          <div className="mgrill-vote-tally">
            <span className="mgrill-vote-up">👍 {voteTally.up}</span>
            <span className="mgrill-vote-down">👎 {voteTally.down}</span>
            <span className="mgrill-vote-total">({voteTally.total} total)</span>
          </div>
          {hasToken ? (
            <div className="mgrill-vote-actions">
              <button
                type="button"
                className={myVote === "up" ? "active" : ""}
                onClick={() =>
                  actions.castVote(playerId, myVote === "up" ? "clear" : "up")
                }
              >
                👍 {myVote === "up" ? "Voted up" : "Vote up"}
              </button>
              <button
                type="button"
                className={myVote === "down" ? "active" : ""}
                onClick={() =>
                  actions.castVote(playerId, myVote === "down" ? "clear" : "down")
                }
              >
                👎 {myVote === "down" ? "Voted down" : "Vote down"}
              </button>
            </div>
          ) : (
            <p className="mgrill-hint">Sign in with a GitHub token to vote.</p>
          )}
          {canActAsCreator && (
            <div className="mgrill-creator-actions">
              {showOverrideConfirm && voteTally.down > 0 ? (
                <div className="mgrill-override-confirm">
                  <p>
                    {voteTally.down} participant(s) voted against this plan.
                    Submit anyway?
                  </p>
                  <button
                    type="button"
                    disabled={submitBusy}
                    onClick={() => handleSubmit(true)}
                  >
                    Submit with override
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowOverrideConfirm(false)}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  className="mgrill-submit-btn"
                  disabled={submitBusy}
                  onClick={() => handleSubmit(false)}
                >
                  {submitBusy ? "Submitting…" : "Submit plan as task"}
                </button>
              )}
              <button
                type="button"
                className="mgrill-keep-btn"
                onClick={() => {
                  setShowOverrideConfirm(false);
                  void actions.keepGrilling();
                }}
              >
                Keep grilling
              </button>
            </div>
          )}
        </div>
      )}

      <div className="mgrill-pending-panel">
        <h3>Pending batch ({pending.length})</h3>
        {pending.length === 0 && (
          <p className="mgrill-pending-empty">Nothing queued yet.</p>
        )}
        <ul className="mgrill-pending-list">
          {pending.map((p) => (
            <li key={p.pending_id} className="mgrill-pending-item">
              <span className="mgrill-pending-author">[{p.name}]</span>
              <span className="mgrill-pending-content">{p.content}</span>
              {p.player_id === playerId && (
                <button
                  type="button"
                  className="mgrill-pending-remove"
                  onClick={() => actions.removePending(p.pending_id, playerId)}
                  aria-label="Remove this pending message"
                >
                  &times;
                </button>
              )}
            </li>
          ))}
        </ul>

        <div className="mgrill-compose">
          <textarea
            className="mgrill-compose-input"
            placeholder={
              hasToken
                ? "Add an answer to the batch (Enter = add, Shift+Enter = newline)…"
                : "Read-only — add a GitHub token to participate."
            }
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleAddPending();
              }
            }}
            disabled={!hasToken}
            rows={2}
          />
          <div className="mgrill-compose-actions">
            <button
              type="button"
              onClick={handleAddPending}
              disabled={!hasToken || draft.trim().length === 0}
            >
              Add to batch
            </button>
            <button
              type="button"
              className="mgrill-send-btn"
              onClick={handleSend}
              disabled={!hasToken || pending.length === 0 || isThinking}
              title={
                isThinking
                  ? "AI is already thinking"
                  : pending.length === 0
                  ? "No pending messages to send"
                  : "Send the pending batch to the AI"
              }
            >
              Send to AI
              {pending.length > 0 ? ` (${pending.length})` : ""}
            </button>
          </div>
        </div>
      </div>

      {actions.error && (
        <p className="mgrill-error" role="alert">
          {actions.error}
        </p>
      )}

      {sessionId && (
        <p className="mgrill-session-id-hint" title={sessionId}>
          session {sessionId.slice(0, 8)}…
        </p>
      )}
    </div>
  );
}
