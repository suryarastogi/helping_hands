import { type FormEvent, useRef, useState, useEffect, useMemo } from "react";

import type { Backend, FormState } from "../types";
import { backendDisplayName, defaultModelForBackend } from "../App.utils";
import RepoChipInput from "./RepoChipInput";
import RepoSuggestInput from "./RepoSuggestInput";

export interface SubmissionFormProps {
  form: FormState;
  onFieldChange: <K extends keyof FormState>(key: K, value: FormState[K]) => void;
  onSubmit: (event: FormEvent) => void;
  backends: Backend[];
  recentRepos?: string[];
  /** Whether the server has GITHUB_TOKEN set. When false, the token field becomes required. */
  serverHasGithubToken?: boolean;
}

export default function SubmissionForm({
  form,
  onFieldChange,
  onSubmit,
  backends,
  recentRepos = [],
  serverHasGithubToken = true,
}: SubmissionFormProps) {
  const [expanded, setExpanded] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-expand when prompt contains newlines (e.g. pre-populated from issue)
  useEffect(() => {
    if (!expanded && form.prompt.includes("\n")) {
      setExpanded(true);
    }
  }, [form.prompt, expanded]);

  // Focus the newly-visible input after toggle
  useEffect(() => {
    if (expanded) {
      textareaRef.current?.focus();
    } else {
      inputRef.current?.focus();
    }
  }, [expanded]);

  const tokenRequired = !serverHasGithubToken;
  const referenceChips = useMemo(
    () =>
      form.reference_repos
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0),
    [form.reference_repos],
  );

  const setReferenceChips = (repos: string[]) => {
    onFieldChange("reference_repos", repos.join(", "));
  };

  return (
    <section className="card form-card compact-form">
      <form onSubmit={onSubmit} className="form-grid-compact">
        <div className="form-inline-row">
          <RepoSuggestInput
            className="repo-input"
            value={form.repo_path}
            onChange={(val) => onFieldChange("repo_path", val)}
            suggestions={recentRepos}
            required
            placeholder="owner/repo"
            ariaLabel="Repository path"
          />
          {!expanded && (
            <input
              ref={inputRef}
              className="prompt-input"
              value={form.prompt}
              onChange={(event) => onFieldChange("prompt", event.target.value)}
              required
              placeholder="Prompt"
              aria-label="Task prompt"
            />
          )}
          <button
            type="button"
            className={`prompt-toggle-btn${expanded ? " expanded" : ""}`}
            onClick={() => setExpanded((v) => !v)}
            aria-label={expanded ? "Switch to inline prompt" : "Switch to multiline prompt"}
            title={expanded ? "Collapse" : "Expand"}
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="4,6 8,10 12,6" />
            </svg>
          </button>
          <button type="submit" className="submit-inline">Run</button>
        </div>
        <div className={`prompt-expanded-row${expanded ? " open" : ""}`} aria-hidden={!expanded}>
          <textarea
            ref={textareaRef}
            className="prompt-input prompt-multiline"
            value={form.prompt}
            onChange={(event) => onFieldChange("prompt", event.target.value)}
            required={expanded}
            placeholder="Prompt (multiline)"
            aria-label="Task prompt (multiline)"
            rows={6}
            tabIndex={expanded ? 0 : -1}
          />
        </div>

        <details className="compact-advanced">
          <summary>Advanced</summary>
          <div className="compact-advanced-body">
            <div className="row two-col">
              <label>
                Backend
                <select
                  value={form.backend}
                  onChange={(event) => onFieldChange("backend", event.target.value as Backend)}
                >
                  {backends.map((backend) => (
                    <option key={backend} value={backend}>
                      {backendDisplayName(backend)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Model
                <input
                  value={form.model}
                  onChange={(event) => onFieldChange("model", event.target.value)}
                  placeholder={defaultModelForBackend(form.backend) || "model"}
                />
              </label>
            </div>
            <div className="row two-col">
              <label>
                Max iterations
                <input
                  type="number"
                  min={1}
                  value={form.max_iterations}
                  onChange={(event) =>
                    onFieldChange("max_iterations", Math.max(1, Number(event.target.value || 1)))
                  }
                />
              </label>
            </div>
            <div className="row check-grid">
              <label className="check-row compact-check">
                <input
                  type="checkbox"
                  checked={form.enable_web}
                  onChange={(event) => onFieldChange("enable_web", event.target.checked)}
                />
                Web
              </label>
            </div>
            <div className="row">
              <label>
                GitHub Token{tokenRequired && <span className="required-star"> *</span>}
                {" "}
                <span className="token-info-icon" title="Requires repo scope. Add workflow scope to enable Fix CI.">&#9432;</span>
                <input
                  className="github-token-input"
                  type="password"
                  value={form.github_token}
                  onChange={(event) => onFieldChange("github_token", event.target.value)}
                  placeholder={tokenRequired ? "ghp_... (required — no server token)" : "ghp_... (optional)"}
                  required={tokenRequired}
                />
              </label>
            </div>
            <details className="compact-advanced">
              <summary>Advanced Github</summary>
              <div className="compact-advanced-body">
                <div className="row two-col">
                  <label>
                    Issue number
                    <input
                      type="number"
                      min={1}
                      value={form.issue_number}
                      onChange={(event) => onFieldChange("issue_number", event.target.value)}
                      placeholder="Link to GitHub issue"
                    />
                  </label>
                  <label>
                    PR number
                    <input
                      type="number"
                      min={1}
                      value={form.pr_number}
                      onChange={(event) => onFieldChange("pr_number", event.target.value)}
                    />
                  </label>
                </div>
                <div className="row check-grid">
                  <label className="check-row compact-check">
                    <input
                      type="checkbox"
                      checked={form.no_pr}
                      onChange={(event) => onFieldChange("no_pr", event.target.checked)}
                    />
                    No PR
                  </label>
                  <label className="check-row compact-check">
                    <input
                      type="checkbox"
                      checked={form.fix_ci}
                      onChange={(event) => onFieldChange("fix_ci", event.target.checked)}
                    />
                    Fix CI
                  </label>
                  <label className="check-row compact-check">
                    <input
                      type="checkbox"
                      checked={form.fix_conflicts}
                      onChange={(event) => onFieldChange("fix_conflicts", event.target.checked)}
                    />
                    AI Fix Conflicts
                  </label>
                  <label className="check-row compact-check">
                    <input
                      type="checkbox"
                      checked={form.master_rebase}
                      onChange={(event) => onFieldChange("master_rebase", event.target.checked)}
                    />
                    AI Master Rebase
                  </label>
                </div>
              </div>
            </details>
            <div className="row">
              <label>
                Reference Repos
                <RepoChipInput
                  value={referenceChips}
                  onChange={setReferenceChips}
                  suggestions={recentRepos}
                  placeholder="owner/repo (optional, read-only)"
                  ariaLabel="Reference repos"
                />
              </label>
            </div>
          </div>
        </details>
      </form>
    </section>
  );
}
