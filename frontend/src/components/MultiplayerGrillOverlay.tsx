/**
 * MultiplayerGrillOverlay — overlay opened from the world's grill pit.
 *
 * Lists currently active multiplayer grill sessions (shared via Yjs),
 * lets any player open one to participate, and lets the local player
 * create a new session. Within a session, the chat is read-write for all
 * participants; the final plan can be voted up/down by anyone, but only
 * the original creator can submit it as a build task.
 */
import {
  type FormEvent,
  type KeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { apiUrl, defaultModelForBackend, saveGithubToken } from "../App.utils";
import type {
  GrillFormState,
  GrillMessage,
  GrillStartResponse,
  MultiplayerGrillSession,
  MultiplayerGrillVote,
} from "../types";
import type { MultiplayerGrillChatState } from "../hooks/useMultiplayerGrillChat";
import RepoChipInput from "./RepoChipInput";
import RepoSuggestInput from "./RepoSuggestInput";

const FORM_DRAFT_KEY = "hh_mp_grill_form_draft";
const CHAT_DRAFT_KEY_PREFIX = "hh_mp_grill_chat_draft:";

// ---------------------------------------------------------------------------
// Draft persistence
// ---------------------------------------------------------------------------

function loadFormDraft(): Partial<GrillFormState> | null {
  try {
    const raw = localStorage.getItem(FORM_DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed !== null ? parsed : null;
  } catch {
    return null;
  }
}

function saveFormDraft(form: GrillFormState): void {
  try {
    const { github_token: _t, ...draft } = form;
    void _t;
    localStorage.setItem(FORM_DRAFT_KEY, JSON.stringify(draft));
  } catch {
    /* ignore */
  }
}

function clearFormDraft(): void {
  try {
    localStorage.removeItem(FORM_DRAFT_KEY);
  } catch {
    /* ignore */
  }
}

function loadChatDraft(sessionId: string): string {
  try {
    return localStorage.getItem(`${CHAT_DRAFT_KEY_PREFIX}${sessionId}`) ?? "";
  } catch {
    return "";
  }
}

function saveChatDraft(sessionId: string, text: string): void {
  try {
    if (text) {
      localStorage.setItem(`${CHAT_DRAFT_KEY_PREFIX}${sessionId}`, text);
    } else {
      localStorage.removeItem(`${CHAT_DRAFT_KEY_PREFIX}${sessionId}`);
    }
  } catch {
    /* ignore */
  }
}

// ---------------------------------------------------------------------------
// Markdown renderer (mirrors GrillMeOverlay)
// ---------------------------------------------------------------------------

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderMarkdown(md: string): string {
  let html = md.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    (_m, lang, code) =>
      `<pre class="grill-code-block"><code class="language-${escapeHtml(lang)}">${escapeHtml(code.trimEnd())}</code></pre>`,
  );
  html = html.replace(/`([^`]+)`/g, (_m, code) => `<code class="grill-inline-code">${escapeHtml(code)}</code>`);
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  html = html.replace(/^### (.+)$/gm, '<h4 class="grill-h">$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3 class="grill-h">$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2 class="grill-h">$1</h2>');
  html = html.replace(/^- (.+)$/gm, '<li class="grill-li">$1</li>');
  html = html.replace(
    /(<li class="grill-li">[\s\S]*?<\/li>)/g,
    '<ul class="grill-ul">$1</ul>',
  );
  html = html.replace(/<\/ul>\s*<ul class="grill-ul">/g, "");
  html = html.replace(/^\d+\. (.+)$/gm, '<li class="grill-li">$1</li>');
  html = html.replace(/\n\n/g, "</p><p>");
  html = `<p>${html}</p>`;
  html = html.replace(/<p>\s*<\/p>/g, "");
  html = html.replace(/\n/g, "<br/>");
  html = html.replace(/<pre([^>]*)>([\s\S]*?)<\/pre>/g, (_m, attrs, inner) =>
    `<pre${attrs}>${inner.replace(/<br\/>/g, "\n")}</pre>`,
  );
  return html;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SessionListPhase({
  sessions,
  onJoin,
  onCreate,
}: {
  sessions: MultiplayerGrillSession[];
  onJoin: (id: string) => void;
  onCreate: () => void;
}) {
  const active = sessions.filter((s) => !s.submitted);
  const past = sessions.filter((s) => s.submitted);

  return (
    <div className="mp-grill-list">
      <div className="mp-grill-list-header">
        <p className="mp-grill-list-tip">
          Join an existing grill session to share the conversation, or start a
          new one.
        </p>
        <button
          type="button"
          className="grill-start-btn"
          onClick={onCreate}
        >
          Start a New Grill
        </button>
      </div>
      {active.length === 0 && past.length === 0 && (
        <div className="mp-grill-list-empty">
          No grill sessions yet — be the first to start one!
        </div>
      )}
      {active.length > 0 && (
        <div className="mp-grill-list-section">
          <h3 className="mp-grill-list-section-title">Active Sessions</h3>
          <ul className="mp-grill-session-list">
            {active.map((s) => (
              <SessionListItem key={s.id} session={s} onJoin={onJoin} />
            ))}
          </ul>
        </div>
      )}
      {past.length > 0 && (
        <div className="mp-grill-list-section">
          <h3 className="mp-grill-list-section-title">Submitted</h3>
          <ul className="mp-grill-session-list">
            {past.map((s) => (
              <SessionListItem key={s.id} session={s} onJoin={onJoin} />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SessionListItem({
  session,
  onJoin,
}: {
  session: MultiplayerGrillSession;
  onJoin: (id: string) => void;
}) {
  const voteCount = Object.keys(session.votes ?? {}).length;
  const upVotes = Object.values(session.votes ?? {}).filter((v) => v === "up").length;
  const downVotes = Object.values(session.votes ?? {}).filter((v) => v === "down").length;
  return (
    <li className="mp-grill-session-row">
      <button
        type="button"
        className="mp-grill-session-card"
        onClick={() => onJoin(session.id)}
        title="Join this session"
      >
        <div className="mp-grill-session-card-head">
          <span
            className="mp-grill-session-creator"
            style={{ color: session.creatorColor }}
          >
            {session.creatorName}
          </span>
          <span className="mp-grill-session-status">{session.status}</span>
        </div>
        <div className="mp-grill-session-repo">{session.repoPath}</div>
        <div className="mp-grill-session-prompt">{session.prompt}</div>
        <div className="mp-grill-session-meta">
          <span>{session.backend}</span>
          {voteCount > 0 && (
            <span className="mp-grill-session-votes">
              {upVotes > 0 && <span title="thumbs up">&#x1F44D; {upVotes}</span>}
              {downVotes > 0 && <span title="thumbs down">&#x1F44E; {downVotes}</span>}
            </span>
          )}
          {session.submitted && <span className="mp-grill-submitted-tag">Submitted</span>}
        </div>
      </button>
    </li>
  );
}

function NewSessionForm({
  onStart,
  onCancel,
  isLoading,
  error,
  recentRepos,
  serverHasGithubToken,
  initialForm,
}: {
  onStart: (form: GrillFormState) => void;
  onCancel: () => void;
  isLoading: boolean;
  error: string | null;
  recentRepos: string[];
  serverHasGithubToken: boolean;
  initialForm: GrillFormState;
}) {
  const [form, setForm] = useState<GrillFormState>(() => {
    const draft = loadFormDraft();
    return draft
      ? { ...initialForm, ...draft, github_token: initialForm.github_token }
      : initialForm;
  });
  const tokenRequired = !serverHasGithubToken;

  useEffect(() => {
    saveFormDraft(form);
  }, [form]);

  const referenceChips = useMemo(
    () =>
      form.reference_repos
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0),
    [form.reference_repos],
  );

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    clearFormDraft();
    onStart(form);
  };

  return (
    <form onSubmit={handleSubmit} className="grill-form">
      <div className="grill-form-field">
        <label>
          Repository
          <RepoSuggestInput
            className="repo-input"
            value={form.repo_path}
            onChange={(val) => setForm((f) => ({ ...f, repo_path: val }))}
            suggestions={recentRepos}
            required
            placeholder="owner/repo"
            ariaLabel="Repository path"
          />
        </label>
      </div>
      <div className="grill-form-field">
        <label>
          What do you want to be grilled about?
          <textarea
            className="grill-prompt-input"
            value={form.prompt}
            onChange={(e) => setForm((f) => ({ ...f, prompt: e.target.value }))}
            required
            placeholder="Describe your plan, design, or feature..."
            rows={3}
          />
        </label>
      </div>
      <div className="grill-form-row">
        <label>
          Backend
          <select
            value={form.backend}
            onChange={(e) => setForm((f) => ({ ...f, backend: e.target.value }))}
            aria-label="AI backend"
          >
            <option value="claudecodecli">Claude Code CLI</option>
            <option value="codexcli">Codex CLI</option>
          </select>
        </label>
        <label>
          Model
          <input
            value={form.model}
            onChange={(e) => setForm((f) => ({ ...f, model: e.target.value }))}
            placeholder={defaultModelForBackend(form.backend || "claudecodecli") || "model"}
          />
        </label>
        <label>
          <span>
            GitHub Token
            {tokenRequired && <span className="required-star"> *</span>}
          </span>
          <input
            type="password"
            value={form.github_token}
            onChange={(e) => setForm((f) => ({ ...f, github_token: e.target.value }))}
            placeholder={tokenRequired ? "ghp_... (required)" : "ghp_... (optional)"}
            required={tokenRequired}
          />
        </label>
      </div>
      <div className="grill-form-field">
        <label>
          Reference Repos
          <RepoChipInput
            value={referenceChips}
            onChange={(repos) => setForm((f) => ({ ...f, reference_repos: repos.join(", ") }))}
            suggestions={recentRepos}
            placeholder="owner/repo (optional, read-only)"
            ariaLabel="Reference repos"
          />
        </label>
      </div>
      {error && <div className="grill-error">{error}</div>}
      <div className="mp-grill-form-actions">
        <button type="button" onClick={onCancel} className="grill-continue-btn">
          Back
        </button>
        <button type="submit" disabled={isLoading} className="grill-start-btn">
          {isLoading ? "Starting..." : "Start Grilling"}
        </button>
      </div>
    </form>
  );
}

function ChatMessage({ message }: { message: GrillMessage }) {
  const isUser = message.role === "user";
  if (message.role === "system") {
    return (
      <div className={`grill-msg grill-msg-system${message.type === "error" ? " grill-msg-error" : ""}`}>
        {message.content}
      </div>
    );
  }
  return (
    <div className={`grill-msg ${isUser ? "grill-msg-user" : "grill-msg-ai"}`}>
      <div className="grill-msg-role">{isUser ? "User" : "Interviewer"}</div>
      <div
        className="grill-msg-content"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
      />
    </div>
  );
}

function VotePanel({
  session,
  myVote,
  onVote,
}: {
  session: MultiplayerGrillSession;
  myVote: MultiplayerGrillVote | null;
  onVote: (vote: MultiplayerGrillVote | null) => void;
}) {
  const upVotes = Object.values(session.votes ?? {}).filter((v) => v === "up").length;
  const downVotes = Object.values(session.votes ?? {}).filter((v) => v === "down").length;
  return (
    <div className="mp-grill-vote-panel">
      <span className="mp-grill-vote-label">Vote on this plan:</span>
      <button
        type="button"
        className={`mp-grill-vote-btn${myVote === "up" ? " mp-grill-vote-active" : ""}`}
        onClick={() => onVote(myVote === "up" ? null : "up")}
        aria-label="Vote up"
        aria-pressed={myVote === "up"}
      >
        &#x1F44D; {upVotes}
      </button>
      <button
        type="button"
        className={`mp-grill-vote-btn${myVote === "down" ? " mp-grill-vote-active" : ""}`}
        onClick={() => onVote(myVote === "down" ? null : "down")}
        aria-label="Vote down"
        aria-pressed={myVote === "down"}
      >
        &#x1F44E; {downVotes}
      </button>
    </div>
  );
}

function SessionDetailPhase({
  session,
  chat,
  isCreator,
  myVote,
  onLeave,
  onVote,
  onSubmit,
}: {
  session: MultiplayerGrillSession;
  chat: MultiplayerGrillChatState;
  isCreator: boolean;
  myVote: MultiplayerGrillVote | null;
  onLeave: () => void;
  onVote: (vote: MultiplayerGrillVote | null) => void;
  onSubmit: () => void;
}) {
  const [input, setInput] = useState<string>(() => loadChatDraft(session.id));
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat.messages, chat.isLoading]);

  useEffect(() => {
    saveChatDraft(session.id, input);
  }, [session.id, input]);

  // Switching sessions resets the input from that session's draft.
  useEffect(() => {
    setInput(loadChatDraft(session.id));
  }, [session.id]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || chat.isLoading) return;
    setInput("");
    saveChatDraft(session.id, "");
    void chat.sendMessage(text);
    requestAnimationFrame(() => inputRef.current?.focus());
  }, [input, chat, session.id]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const showPlan = chat.finalPlan !== null;

  return (
    <div className="mp-grill-detail">
      <div className="mp-grill-detail-header">
        <button
          type="button"
          className="mp-grill-back-btn"
          onClick={onLeave}
          aria-label="Back to sessions"
        >
          &larr; Sessions
        </button>
        <div className="mp-grill-detail-meta">
          <div>
            <span
              className="mp-grill-detail-creator"
              style={{ color: session.creatorColor }}
            >
              {session.creatorName}
            </span>
            <span className="mp-grill-detail-repo">{session.repoPath}</span>
          </div>
          <div className="mp-grill-detail-prompt">{session.prompt}</div>
        </div>
      </div>

      <div className="grill-chat">
        <div className="grill-chat-messages">
          {chat.messages.map((m) => (
            <ChatMessage key={m.id} message={m} />
          ))}
          {chat.isLoading && (
            <div className="grill-msg grill-msg-ai grill-msg-thinking">
              <div className="grill-msg-role">Interviewer</div>
              <div className="grill-thinking-dots">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}
          {chat.error && <div className="grill-error">{chat.error}</div>}
          <div ref={chatEndRef} />
        </div>

        {!showPlan && !session.submitted && (
          <div className="grill-chat-input-row">
            <textarea
              ref={inputRef}
              className="grill-chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message... (Enter to send, Shift+Enter for newline)"
              rows={2}
              disabled={chat.isLoading}
            />
            <div className="grill-chat-actions">
              <button
                type="button"
                onClick={handleSend}
                disabled={chat.isLoading || !input.trim()}
                className="grill-send-btn"
              >
                Send
              </button>
              <button
                type="button"
                onClick={() => void chat.requestPlan()}
                disabled={chat.isLoading}
                className="grill-plan-btn"
                title="Wrap up and produce the final plan"
              >
                Wrap Up
              </button>
            </div>
          </div>
        )}
      </div>

      {showPlan && chat.finalPlan && (
        <div className="grill-plan mp-grill-plan">
          <div
            className="grill-plan-content"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(chat.finalPlan) }}
          />
          <VotePanel session={session} myVote={myVote} onVote={onVote} />
          <div className="grill-plan-actions">
            {isCreator ? (
              <button
                type="button"
                onClick={onSubmit}
                disabled={session.submitted}
                className="grill-confirm-btn"
              >
                {session.submitted ? "Already Submitted" : "Submit as Task"}
              </button>
            ) : (
              <span className="mp-grill-only-creator">
                Only {session.creatorName} can submit this plan.
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main overlay
// ---------------------------------------------------------------------------

export interface MultiplayerGrillOverlayProps {
  sessions: MultiplayerGrillSession[];
  selectedSessionId: string | null;
  onSelectSession: (id: string | null) => void;
  recentRepos: string[];
  serverHasGithubToken: boolean;
  initialForm: GrillFormState;
  localPlayerId: string;
  chat: MultiplayerGrillChatState;
  onClose: () => void;
  /** Creates a new session on the server and adds it to shared state. */
  onCreateSession: (form: GrillFormState) => Promise<string | null>;
  onVote: (id: string, vote: MultiplayerGrillVote | null) => void;
  /** Submit the final plan as a build task (creator only). */
  onSubmitPlan: (session: MultiplayerGrillSession, plan: string) => void;
}

export default function MultiplayerGrillOverlay({
  sessions,
  selectedSessionId,
  onSelectSession,
  recentRepos,
  serverHasGithubToken,
  initialForm,
  localPlayerId,
  chat,
  onClose,
  onCreateSession,
  onVote,
  onSubmitPlan,
}: MultiplayerGrillOverlayProps) {
  const [showNewForm, setShowNewForm] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const selectedSession = useMemo(
    () => sessions.find((s) => s.id === selectedSessionId) ?? null,
    [sessions, selectedSessionId],
  );

  // If the selected session disappears (creator deleted it), bail back.
  useEffect(() => {
    if (selectedSessionId && !selectedSession) {
      onSelectSession(null);
    }
  }, [selectedSessionId, selectedSession, onSelectSession]);

  const handleCreate = useCallback(
    async (form: GrillFormState) => {
      setCreateError(null);
      setCreating(true);
      try {
        if (form.github_token?.trim()) {
          saveGithubToken(form.github_token);
        }
        const sid = await onCreateSession(form);
        if (sid) {
          setShowNewForm(false);
          onSelectSession(sid);
        }
      } catch (err) {
        setCreateError(err instanceof Error ? err.message : String(err));
      } finally {
        setCreating(false);
      }
    },
    [onCreateSession, onSelectSession],
  );

  const handleSubmit = useCallback(() => {
    if (!selectedSession) return;
    if (!chat.finalPlan) return;
    onSubmitPlan(selectedSession, chat.finalPlan);
  }, [selectedSession, chat.finalPlan, onSubmitPlan]);

  const isCreator =
    !!selectedSession && selectedSession.creatorId === localPlayerId;
  const myVote = selectedSession
    ? (selectedSession.votes?.[localPlayerId] ?? null)
    : null;

  let title = "Grill Pit";
  if (showNewForm) title = "New Grill Session";
  else if (selectedSession) title = `Grilling: ${selectedSession.creatorName}'s Plan`;

  return (
    <div className="grill-overlay mp-grill-overlay" onClick={onClose}>
      <div className="grill-overlay-content mp-grill-overlay-content" onClick={(e) => e.stopPropagation()}>
        <div className="grill-overlay-header">
          <h2 className="grill-overlay-title">{title}</h2>
          <button
            type="button"
            className="grill-overlay-close"
            onClick={onClose}
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        {showNewForm && (
          <NewSessionForm
            onStart={handleCreate}
            onCancel={() => setShowNewForm(false)}
            isLoading={creating}
            error={createError}
            recentRepos={recentRepos}
            serverHasGithubToken={serverHasGithubToken}
            initialForm={initialForm}
          />
        )}

        {!showNewForm && !selectedSession && (
          <SessionListPhase
            sessions={sessions}
            onJoin={(id) => onSelectSession(id)}
            onCreate={() => setShowNewForm(true)}
          />
        )}

        {!showNewForm && selectedSession && (
          <SessionDetailPhase
            session={selectedSession}
            chat={chat}
            isCreator={isCreator}
            myVote={myVote}
            onLeave={() => onSelectSession(null)}
            onVote={(vote) => onVote(selectedSession.id, vote)}
            onSubmit={handleSubmit}
          />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helper exposed for App.tsx — POST /grill and return the session id.
// ---------------------------------------------------------------------------

export async function createMultiplayerGrillSession(
  form: GrillFormState,
): Promise<{ sessionId: string; status: string } | { error: string }> {
  const refRepos = form.reference_repos
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  try {
    const res = await fetch(apiUrl("/grill"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repo_path: form.repo_path,
        prompt: form.prompt,
        model: form.model || null,
        github_token: form.github_token || null,
        reference_repos: refRepos,
        backend: form.backend || "claudecodecli",
      }),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      const detail = (errData as { detail?: string }).detail ?? `HTTP ${res.status}`;
      return { error: detail };
    }
    const data = (await res.json()) as GrillStartResponse;
    return { sessionId: data.session_id, status: data.status };
  } catch (err) {
    return { error: err instanceof Error ? err.message : String(err) };
  }
}
