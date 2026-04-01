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
}: {
  onStart: (form: GrillFormState) => void;
  isLoading: boolean;
  error: string | null;
  recentRepos: string[];
  serverHasGithubToken: boolean;
  initialForm: GrillFormState;
}) {
  const [form, setForm] = useState<GrillFormState>(initialForm);
  const tokenRequired = !serverHasGithubToken;

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
          Model
          <input
            value={form.model}
            onChange={(e) => setForm((f) => ({ ...f, model: e.target.value }))}
            placeholder={defaultModelForBackend("claudecodecli") || "model"}
          />
        </label>
        <label>
          GitHub Token{tokenRequired && <span className="required-star"> *</span>}
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
      <button type="submit" disabled={isLoading} className="grill-start-btn">
        {isLoading ? "Starting..." : "Start Grilling"}
      </button>
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
  const [input, setInput] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const groups = useMemo(() => groupMessages(messages), [messages]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput("");
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

export default function GrillMeOverlay({
  session,
  recentRepos,
  serverHasGithubToken,
  initialForm,
  onClose,
  onSubmitPlan,
}: GrillMeOverlayProps) {
  const handleConfirmPlan = useCallback(() => {
    if (session.finalPlan) {
      onSubmitPlan(session.finalPlan);
    }
  }, [session.finalPlan, onSubmitPlan]);

  const handleContinueGrilling = useCallback(() => {
    // Go back to chat phase — the session is still active
    // We need to send a message to continue
    session.sendMessage("Actually, I have more questions. Let's continue grilling.");
  }, [session]);

  const phaseTitle: Record<GrillPhase, string> = {
    form: "Grill Me",
    chatting: "Grilling in Progress",
    plan: "Final Plan",
  };

  return (
    <div className="grill-overlay" onClick={onClose}>
      <div className="grill-overlay-content" onClick={(e) => e.stopPropagation()}>
        <div className="grill-overlay-header">
          <h2 className="grill-overlay-title">{phaseTitle[session.phase]}</h2>
          <button
            type="button"
            className="grill-overlay-close"
            onClick={onClose}
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        {session.phase === "form" && (
          <GrillFormPhase
            onStart={session.startSession}
            isLoading={session.isLoading}
            error={session.error}
            recentRepos={recentRepos}
            serverHasGithubToken={serverHasGithubToken}
            initialForm={initialForm}
          />
        )}

        {session.phase === "chatting" && (
          <GrillChatPhase
            messages={session.messages}
            isLoading={session.isLoading}
            error={session.error}
            onSend={session.sendMessage}
            onRequestPlan={session.requestPlan}
          />
        )}

        {session.phase === "plan" && session.finalPlan && (
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
