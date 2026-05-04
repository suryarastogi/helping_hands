import { type FormEvent, useCallback, useEffect, useState } from "react";

import { apiUrl } from "../App.utils";
import RepoSuggestInput from "./RepoSuggestInput";

const REPO_DRAFT_KEY = "hh_submit_issue_repo_draft";

function loadRepoDraft(): string {
  try {
    return localStorage.getItem(REPO_DRAFT_KEY) ?? "";
  } catch {
    return "";
  }
}

function saveRepoDraft(value: string): void {
  try {
    if (value) {
      localStorage.setItem(REPO_DRAFT_KEY, value);
    } else {
      localStorage.removeItem(REPO_DRAFT_KEY);
    }
  } catch {
    /* ignore */
  }
}

type GitHubIssue = {
  number: number;
  title: string;
  body: string;
  url: string;
  state: string;
  labels: string[];
  user: string;
};

type Step = "repo" | "issues";

export interface SubmitIssueOverlayProps {
  recentRepos: string[];
  serverHasGithubToken: boolean;
  defaultRepo?: string;
  onSubmitIssue: (repo: string, issue: GitHubIssue, githubToken: string) => void;
  onClose: () => void;
  githubToken?: string;
}

export default function SubmitIssueOverlay({
  recentRepos,
  serverHasGithubToken,
  defaultRepo = "",
  onSubmitIssue,
  onClose,
  githubToken: githubTokenProp = "",
}: SubmitIssueOverlayProps) {
  const [step, setStep] = useState<Step>("repo");
  // Prefer a persisted draft so the user's in-progress input survives
  // close/reopen; fall back to the caller-supplied defaultRepo.
  const [repo, setRepo] = useState<string>(() => loadRepoDraft() || defaultRepo);
  const githubToken = githubTokenProp;
  const [issues, setIssues] = useState<GitHubIssue[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Persist the repo draft on every change.
  useEffect(() => {
    saveRepoDraft(repo);
  }, [repo]);

  const tokenRequired = !serverHasGithubToken && !githubToken.trim();

  const fetchIssues = useCallback(async () => {
    const trimmed = repo.trim();
    if (!trimmed) return;
    const parts = trimmed.split("/");
    if (parts.length !== 2) {
      setError("Enter a valid owner/repo");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({ state: "open", per_page: "30" });
      if (githubToken.trim()) {
        params.set("github_token", githubToken.trim());
      }
      const res = await fetch(
        apiUrl(`/repos/${parts[0]}/${parts[1]}/issues?${params.toString()}`),
      );
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `HTTP ${res.status}`);
      }
      const data = (await res.json()) as GitHubIssue[];
      setIssues(data);
      setStep("issues");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [repo, githubToken]);

  const handleRepoSubmit = (e: FormEvent) => {
    e.preventDefault();
    void fetchIssues();
  };

  // Reset issues when going back
  const handleBack = () => {
    setStep("repo");
    setIssues([]);
    setError(null);
  };

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="grill-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div
        className="grill-overlay-content"
      >
        <div className="grill-overlay-header">
          <h2 className="grill-overlay-title">
            {step === "repo" ? "Submit Issue" : `Issues — ${repo}`}
          </h2>
          <button
            type="button"
            className="grill-overlay-close"
            onClick={onClose}
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        <div style={{ padding: "16px 20px", overflowY: "auto" }}>
          {step === "repo" && (
            <form onSubmit={handleRepoSubmit}>
              <label>
                Repository
                <RepoSuggestInput
                  className="repo-input"
                  value={repo}
                  onChange={setRepo}
                  suggestions={recentRepos}
                  required
                  placeholder="owner/repo"
                  ariaLabel="Repository path"
                />
              </label>
              {tokenRequired && (
                <p style={{ color: "var(--red, #f44)", marginTop: 8, fontSize: "0.85rem" }}>
                  GitHub token required — set it in the banner above.
                </p>
              )}
              {error && (
                <p style={{ color: "var(--red, #f44)", marginTop: 8 }}>{error}</p>
              )}
              <button
                type="submit"
                className="submit-inline"
                disabled={loading || !repo.trim() || tokenRequired}
                style={{ marginTop: 16, width: "100%" }}
              >
                {loading ? "Loading..." : "Fetch Issues"}
              </button>
            </form>
          )}

          {step === "issues" && (
            <>
              <button
                type="button"
                className="text-button"
                onClick={handleBack}
                style={{ marginBottom: 12 }}
              >
                &larr; Back
              </button>
              {issues.length === 0 ? (
                <p className="empty-list">No open issues found.</p>
              ) : (
                <ul className="issue-list">
                  {issues.map((issue) => (
                    <li key={issue.number}>
                      <button
                        type="button"
                        className="issue-row"
                        onClick={() => { saveRepoDraft(""); onSubmitIssue(repo, issue, githubToken); }}
                      >
                        <span className="issue-row-top">
                          <code>#{issue.number}</code>
                          <span className="issue-title">{issue.title}</span>
                        </span>
                        <span className="issue-row-meta">
                          {issue.user}
                          {issue.labels.length > 0 && ` · ${issue.labels.join(", ")}`}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
