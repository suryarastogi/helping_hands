import { type FormEvent, useMemo } from "react";

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
}

export default function SubmissionForm({
  form,
  onFieldChange,
  onSubmit,
  backends,
  recentRepos = [],
}: SubmissionFormProps) {
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
          <input
            className="prompt-input"
            value={form.prompt}
            onChange={(event) => onFieldChange("prompt", event.target.value)}
            required
            placeholder="Prompt"
            aria-label="Task prompt"
          />
          <button type="submit" className="submit-inline">Run</button>
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
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={form.create_issue}
                  onChange={(event) => onFieldChange("create_issue", event.target.checked)}
                />
                Create issue
              </label>
            </div>
            <label>
              Tools
              <input
                value={form.tools}
                onChange={(event) => onFieldChange("tools", event.target.value)}
                placeholder="execution,web"
              />
            </label>
            <label>
              Skills
              <input
                value={form.skills}
                onChange={(event) => onFieldChange("skills", event.target.value)}
                placeholder="execution,web,prd,ralph"
              />
            </label>
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
                  checked={form.enable_execution}
                  onChange={(event) => onFieldChange("enable_execution", event.target.checked)}
                />
                Execution
              </label>
              <label className="check-row compact-check">
                <input
                  type="checkbox"
                  checked={form.enable_web}
                  onChange={(event) => onFieldChange("enable_web", event.target.checked)}
                />
                Web
              </label>
              <label className="check-row compact-check">
                <input
                  type="checkbox"
                  checked={form.fix_ci}
                  onChange={(event) => onFieldChange("fix_ci", event.target.checked)}
                />
                Fix CI
              </label>
            </div>
            <div className="row">
              <label>
                GitHub Token
                <input
                  type="password"
                  value={form.github_token}
                  onChange={(event) => onFieldChange("github_token", event.target.value)}
                  placeholder="ghp_... (optional)"
                />
              </label>
            </div>
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
