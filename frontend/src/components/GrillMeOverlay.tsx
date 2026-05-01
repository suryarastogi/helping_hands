import {
  type FormEvent,
  type KeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { defaultModelForBackend } from "../App.utils";
import type { GrillFormState, GrillMessage, GrillPhase } from "../types";
import type { GrillSessionState } from "../hooks/useGrillSession";
import RepoChipInput from "./RepoChipInput";
import RepoSuggestInput from "./RepoSuggestInput";

// ---------------------------------------------------------------------------
// Draft persistence — keep user input across overlay close/reopen.
// ---------------------------------------------------------------------------

const FORM_DRAFT_KEY = "hh_grill_form_draft";
const CHAT_DRAFT_KEY = "hh_grill_chat_draft";
const PLAN_HISTORY_KEY = "hh_grill_plan_history";
const PLAN_HISTORY_MAX = 50;

export type GrillPlanHistoryEntry = {
  id: string;
  submittedAt: number;
  repoPath: string;
  prompt: string;
  finalPlan: string;
  messages: GrillMessage[];
};

export function loadPlanHistory(): GrillPlanHistoryEntry[] {
  try {
    const raw = localStorage.getItem(PLAN_HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (entry): entry is GrillPlanHistoryEntry =>
        typeof entry === "object" &&
        entry !== null &&
        typeof entry.id === "string" &&
        typeof entry.finalPlan === "string" &&
        Array.isArray(entry.messages),
    );
  } catch {
    return [];
  }
}

export function savePlanHistoryEntry(entry: GrillPlanHistoryEntry): void {
  try {
    const existing = loadPlanHistory();
    const next = [entry, ...existing].slice(0, PLAN_HISTORY_MAX);
    localStorage.setItem(PLAN_HISTORY_KEY, JSON.stringify(next));
  } catch {
    /* quota exceeded or unavailable — silently ignore */
  }
}

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
    // Don't persist the github token — it's already managed separately
    // via loadGithubToken/saveGithubToken.
    const { github_token: _github_token, ...draft } = form;
    void _github_token;
    localStorage.setItem(FORM_DRAFT_KEY, JSON.stringify(draft));
  } catch {
    /* quota exceeded or unavailable — silently ignore */
  }
}

function clearFormDraft(): void {
  try {
    localStorage.removeItem(FORM_DRAFT_KEY);
  } catch {
    /* ignore */
  }
}

function loadChatDraft(): string {
  try {
    return localStorage.getItem(CHAT_DRAFT_KEY) ?? "";
  } catch {
    return "";
  }
}

function saveChatDraft(text: string): void {
  try {
    if (text) {
      localStorage.setItem(CHAT_DRAFT_KEY, text);
    } else {
      localStorage.removeItem(CHAT_DRAFT_KEY);
    }
  } catch {
    /* ignore */
  }
}

// ---------------------------------------------------------------------------
// Simple markdown renderer (no external deps)
// ---------------------------------------------------------------------------

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderMarkdown(md: string): string {
  // Fenced code blocks
  let html = md.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    (_match, lang, code) =>
      `<pre class="grill-code-block"><code class="language-${escapeHtml(lang)}">${escapeHtml(code.trimEnd())}</code></pre>`,
  );
  // Inline code
  html = html.replace(/`([^`]+)`/g, (_m, code) => `<code class="grill-inline-code">${escapeHtml(code)}</code>`);
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  // Headers
  html = html.replace(/^### (.+)$/gm, '<h4 class="grill-h">$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3 class="grill-h">$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2 class="grill-h">$1</h2>');
  // Unordered lists
  html = html.replace(/^- (.+)$/gm, '<li class="grill-li">$1</li>');
  html = html.replace(
    /(<li class="grill-li">[\s\S]*?<\/li>)/g,
    '<ul class="grill-ul">$1</ul>',
  );
  // Collapse adjacent <ul> tags
  html = html.replace(/<\/ul>\s*<ul class="grill-ul">/g, "");
  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li class="grill-li">$1</li>');
  // Paragraphs (double newline)
  html = html.replace(/\n\n/g, "</p><p>");
  html = `<p>${html}</p>`;
  // Clean up empty paragraphs
  html = html.replace(/<p>\s*<\/p>/g, "");
  // Line breaks within paragraphs
  html = html.replace(/\n/g, "<br/>");
  // Don't break inside pre blocks
  html = html.replace(/<pre([^>]*)>([\s\S]*?)<\/pre>/g, (_m, attrs, inner) =>
    `<pre${attrs}>${inner.replace(/<br\/>/g, "\n")}</pre>`,
  );

  return html;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function GrillFormPhase({
  onStart,
  isLoading,
  error,
  recentRepos,
  serverHasGithubToken,
  initialForm,
  onViewHistory,
  historyCount,
}: {
  onStart: (form: GrillFormState) => void;
  isLoading: boolean;
  error: string | null;
  recentRepos: string[];
  serverHasGithubToken: boolean;
  initialForm: GrillFormState;
  onViewHistory: () => void;
  historyCount: number;
}) {
  // Hydrate from any persisted draft so de-focus/re-focus preserves user input.
  // Token is intentionally not persisted here (managed via saveGithubToken).
  const [form, setForm] = useState<GrillFormState>(() => {
    const draft = loadFormDraft();
    return draft ? { ...initialForm, ...draft, github_token: initialForm.github_token } : initialForm;
  });
  const tokenRequired = !serverHasGithubToken;

  // Persist draft on every change.
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
          <span>GitHub Token{tokenRequired && <span className="required-star"> *</span>} <span className="token-info-icon" title="Requires repo scope. Add workflow scope to enable Fix CI.">&#9432;</span></span>
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
      <div className="grill-form-actions">
        <button type="submit" disabled={isLoading} className="grill-start-btn">
          {isLoading ? "Starting..." : "Start Grilling"}
        </button>
        <button
          type="button"
          onClick={onViewHistory}
          className="grill-history-btn"
          title="View plans submitted from past grilling sessions"
        >
          Past Plans{historyCount > 0 ? ` (${historyCount})` : ""}
        </button>
      </div>
    </form>
  );
}

function GrillChatMessage({ message }: { message: GrillMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`grill-msg ${isUser ? "grill-msg-user" : "grill-msg-ai"}`}>
      <div className="grill-msg-role">{isUser ? "You" : "Interviewer"}</div>
      <div
        className="grill-msg-content"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
      />
    </div>
  );
}

/** A run of consecutive system messages, collapsed to show only the latest. */
function GrillSystemGroup({ messages }: { messages: GrillMessage[] }) {
  const last = messages[messages.length - 1];
  const hasError = messages.some((m) => m.type === "error");

  if (messages.length === 1) {
    return (
      <div className={`grill-msg grill-msg-system${hasError ? " grill-msg-error" : ""}`}>
        {last.content}
      </div>
    );
  }

  return (
    <details className="grill-system-group">
      <summary className={`grill-msg grill-msg-system${hasError ? " grill-msg-error" : ""}`}>
        {last.content}
        <span className="grill-system-count">{messages.length} steps</span>
      </summary>
      <div className="grill-system-details">
        {messages.slice(0, -1).map((m) => (
          <div
            key={m.id}
            className={`grill-system-detail-line${m.type === "error" ? " grill-msg-error" : ""}`}
          >
            {m.content}
          </div>
        ))}
      </div>
    </details>
  );
}

type MessageGroup =
  | { kind: "system"; messages: GrillMessage[] }
  | { kind: "chat"; message: GrillMessage };

/** Group consecutive system messages into collapsible runs. */
function groupMessages(messages: GrillMessage[]): MessageGroup[] {
  const groups: MessageGroup[] = [];
  let systemRun: GrillMessage[] = [];

  const flushSystem = () => {
    if (systemRun.length > 0) {
      groups.push({ kind: "system", messages: systemRun });
      systemRun = [];
    }
  };

  for (const msg of messages) {
    if (msg.role === "system") {
      systemRun.push(msg);
    } else {
      flushSystem();
      groups.push({ kind: "chat", message: msg });
    }
  }
  flushSystem();
  return groups;
}

function GrillChatPhase({
  messages,
  isLoading,
  error,
  onSend,
  onRequestPlan,
}: {
  messages: GrillMessage[];
  isLoading: boolean;
  error: string | null;
  onSend: (content: string) => void;
  onRequestPlan: () => void;
}) {
  // Hydrate the chat input draft so close/reopen preserves the in-flight message.
  const [input, setInput] = useState<string>(loadChatDraft);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const groups = useMemo(() => groupMessages(messages), [messages]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Persist every edit so the draft survives overlay close/reopen.
  useEffect(() => {
    saveChatDraft(input);
  }, [input]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput("");
    saveChatDraft("");
    onSend(text);
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="grill-chat">
      <div className="grill-chat-messages">
        {groups.map((group, i) =>
          group.kind === "system" ? (
            <GrillSystemGroup key={`sys-${i}`} messages={group.messages} />
          ) : (
            <GrillChatMessage key={group.message.id} message={group.message} />
          ),
        )}
        {isLoading && (
          <div className="grill-msg grill-msg-ai grill-msg-thinking">
            <div className="grill-msg-role">Interviewer</div>
            <div className="grill-thinking-dots">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
        {error && <div className="grill-error">{error}</div>}
        <div ref={chatEndRef} />
      </div>
      <div className="grill-chat-input-row">
        <textarea
          ref={inputRef}
          className="grill-chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your answer... (Enter to send, Shift+Enter for newline)"
          rows={2}
          disabled={isLoading}
        />
        <div className="grill-chat-actions">
          <button
            type="button"
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="grill-send-btn"
          >
            Send
          </button>
          <button
            type="button"
            onClick={onRequestPlan}
            disabled={isLoading}
            className="grill-plan-btn"
            title="End grilling and produce the final plan"
          >
            Wrap Up
          </button>
        </div>
      </div>
    </div>
  );
}

function GrillPlanPhase({
  finalPlan,
  onConfirm,
  onContinue,
}: {
  finalPlan: string;
  onConfirm: () => void;
  onContinue: () => void;
}) {
  return (
    <div className="grill-plan">
      <div
        className="grill-plan-content"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(finalPlan) }}
      />
      <div className="grill-plan-actions">
        <button type="button" onClick={onConfirm} className="grill-confirm-btn">
          Submit as Task
        </button>
        <button type="button" onClick={onContinue} className="grill-continue-btn">
          Keep Grilling
        </button>
      </div>
    </div>
  );
}

function formatHistoryTimestamp(ms: number): string {
  try {
    return new Date(ms).toLocaleString();
  } catch {
    return String(ms);
  }
}

function GrillHistoryList({
  entries,
  onSelect,
  onBack,
}: {
  entries: GrillPlanHistoryEntry[];
  onSelect: (entry: GrillPlanHistoryEntry) => void;
  onBack: () => void;
}) {
  return (
    <div className="grill-history-list">
      {entries.length === 0 ? (
        <div className="grill-history-empty">
          No past plans yet. Submitted plans will appear here.
        </div>
      ) : (
        <ul className="grill-history-entries">
          {entries.map((entry) => (
            <li key={entry.id} className="grill-history-entry">
              <button
                type="button"
                className="grill-history-entry-btn"
                onClick={() => onSelect(entry)}
              >
                <div className="grill-history-entry-title">
                  {entry.repoPath || "(no repo)"}
                </div>
                <div className="grill-history-entry-meta">
                  {formatHistoryTimestamp(entry.submittedAt)}
                </div>
                {entry.prompt && (
                  <div className="grill-history-entry-prompt">
                    {entry.prompt.length > 140
                      ? `${entry.prompt.slice(0, 140)}…`
                      : entry.prompt}
                  </div>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="grill-history-actions">
        <button
          type="button"
          onClick={onBack}
          className="grill-history-back-btn"
        >
          Back
        </button>
      </div>
    </div>
  );
}

function GrillHistoryDetail({
  entry,
  onBack,
}: {
  entry: GrillPlanHistoryEntry;
  onBack: () => void;
}) {
  const groups = useMemo(() => groupMessages(entry.messages), [entry.messages]);

  return (
    <div className="grill-history-detail">
      <div className="grill-history-detail-header">
        <div className="grill-history-detail-title">
          {entry.repoPath || "(no repo)"}
        </div>
        <div className="grill-history-detail-meta">
          {formatHistoryTimestamp(entry.submittedAt)}
        </div>
      </div>

      <section className="grill-history-detail-section">
        <h3 className="grill-history-detail-h">Conversation</h3>
        <div className="grill-chat-messages grill-history-detail-messages">
          {groups.map((group, i) =>
            group.kind === "system" ? (
              <GrillSystemGroup key={`sys-${i}`} messages={group.messages} />
            ) : (
              <GrillChatMessage key={group.message.id} message={group.message} />
            ),
          )}
        </div>
      </section>

      <section className="grill-history-detail-section">
        <h3 className="grill-history-detail-h">Final Plan</h3>
        <div
          className="grill-plan-content"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(entry.finalPlan) }}
        />
      </section>

      <div className="grill-history-actions">
        <button
          type="button"
          onClick={onBack}
          className="grill-history-back-btn"
        >
          Back to list
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main overlay
// ---------------------------------------------------------------------------

export interface GrillMeOverlayProps {
  session: GrillSessionState;
  recentRepos: string[];
  serverHasGithubToken: boolean;
  initialForm: GrillFormState;
  onClose: () => void;
  onSubmitPlan: (plan: string) => void;
}

type HistoryView =
  | { kind: "none" }
  | { kind: "list" }
  | { kind: "detail"; entry: GrillPlanHistoryEntry };

export default function GrillMeOverlay({
  session,
  recentRepos,
  serverHasGithubToken,
  initialForm,
  onClose,
  onSubmitPlan,
}: GrillMeOverlayProps) {
  // Snapshot of the form used to start the active session (for history entry).
  const submittedFormRef = useRef<GrillFormState | null>(null);

  // Cached history list — reloaded when we enter history view.
  const [history, setHistory] = useState<GrillPlanHistoryEntry[]>(() =>
    loadPlanHistory(),
  );
  const [historyView, setHistoryView] = useState<HistoryView>({ kind: "none" });

  const handleStartSession = useCallback(
    (form: GrillFormState) => {
      submittedFormRef.current = form;
      void session.startSession(form);
    },
    [session],
  );

  const handleConfirmPlan = useCallback(() => {
    if (!session.finalPlan) return;
    const submitted = submittedFormRef.current;
    const entry: GrillPlanHistoryEntry = {
      id: `plan-${Date.now()}`,
      submittedAt: Date.now(),
      repoPath: submitted?.repo_path ?? initialForm.repo_path ?? "",
      prompt: submitted?.prompt ?? "",
      finalPlan: session.finalPlan,
      messages: session.messages,
    };
    savePlanHistoryEntry(entry);
    setHistory((prev) => [entry, ...prev].slice(0, PLAN_HISTORY_MAX));
    onSubmitPlan(session.finalPlan);
  }, [
    session.finalPlan,
    session.messages,
    initialForm.repo_path,
    onSubmitPlan,
  ]);

  const handleContinueGrilling = useCallback(() => {
    // Go back to chat phase — the session is still active
    // We need to send a message to continue
    session.sendMessage("Actually, I have more questions. Let's continue grilling.");
  }, [session]);

  const handleViewHistory = useCallback(() => {
    setHistory(loadPlanHistory());
    setHistoryView({ kind: "list" });
  }, []);

  const handleSelectHistoryEntry = useCallback(
    (entry: GrillPlanHistoryEntry) => {
      setHistoryView({ kind: "detail", entry });
    },
    [],
  );

  const handleHistoryBackToList = useCallback(() => {
    setHistoryView({ kind: "list" });
  }, []);

  const handleHistoryBackToForm = useCallback(() => {
    setHistoryView({ kind: "none" });
  }, []);

  // Once a session has started on the server (or any chat history exists),
  // closing the overlay will destroy that work — warn before discarding it.
  const hasUserEffort =
    session.sessionId !== null || session.messages.length > 0;

  const handleClose = useCallback(() => {
    if (hasUserEffort) {
      const ok = window.confirm(
        "Close Grill Me? Your grilling session will be discarded and cannot be resumed.",
      );
      if (!ok) return;
    }
    onClose();
  }, [hasUserEffort, onClose]);

  const phaseTitle: Record<GrillPhase, string> = {
    form: "Grill Me",
    chatting: "Grilling in Progress",
    plan: "Final Plan",
  };

  const viewingHistory = historyView.kind !== "none";
  const headerTitle = viewingHistory
    ? historyView.kind === "detail"
      ? "Past Plan"
      : "Past Plans"
    : phaseTitle[session.phase];

  return (
    <div className="grill-overlay" onClick={handleClose}>
      <div className="grill-overlay-content" onClick={(e) => e.stopPropagation()}>
        <div className="grill-overlay-header">
          <h2 className="grill-overlay-title">{headerTitle}</h2>
          <button
            type="button"
            className="grill-overlay-close"
            onClick={handleClose}
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        {historyView.kind === "list" && (
          <GrillHistoryList
            entries={history}
            onSelect={handleSelectHistoryEntry}
            onBack={handleHistoryBackToForm}
          />
        )}

        {historyView.kind === "detail" && (
          <GrillHistoryDetail
            entry={historyView.entry}
            onBack={handleHistoryBackToList}
          />
        )}

        {!viewingHistory && session.phase === "form" && (
          <GrillFormPhase
            onStart={handleStartSession}
            isLoading={session.isLoading}
            error={session.error}
            recentRepos={recentRepos}
            serverHasGithubToken={serverHasGithubToken}
            initialForm={initialForm}
            onViewHistory={handleViewHistory}
            historyCount={history.length}
          />
        )}

        {!viewingHistory && session.phase === "chatting" && (
          <GrillChatPhase
            messages={session.messages}
            isLoading={session.isLoading}
            error={session.error}
            onSend={session.sendMessage}
            onRequestPlan={session.requestPlan}
          />
        )}

        {!viewingHistory && session.phase === "plan" && session.finalPlan && (
          <GrillPlanPhase
            finalPlan={session.finalPlan}
            onConfirm={handleConfirmPlan}
            onContinue={handleContinueGrilling}
          />
        )}
      </div>
    </div>
  );
}
