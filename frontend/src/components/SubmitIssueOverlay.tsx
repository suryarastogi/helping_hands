import { type FormEvent, useCallback, useEffect, useState } from "react";

import { apiUrl } from "../App.utils";
import RepoSuggestInput from "./RepoSuggestInput";

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
}

export default function SubmitIssueOverlay({
  recentRepos,
  serverHasGithubToken,
  defaultRepo = "",
  onSubmitIssue,
  onClose,
}: SubmitIssueOverlayProps) {
  const [step, setStep] = useState<Step>("repo");
  const [repo, setRepo] = useState(defaultRepo);
  const [githubToken, setGithubToken] = useState("");
  const [issues, setIssues] = useState<GitHubIssue[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    <div className="grill-overlay" onClick={onClose}>
      <div
        className="grill-overlay-content"
        onClick={(e) => e.stopPropagation()}
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
              <label style={{ marginTop: 12, display: "block" }}>
                GitHub Token{!serverHasGithubToken && <span className="required-star"> *</span>}
                <input
                  className="github-token-input"
                  type="password"
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  placeholder={serverHasGithubToken ? "ghp_... (optional)" : "ghp_... (required)"}
                  required={!serverHasGithubToken}
                  style={{ width: "100%", marginTop: 4 }}
                />
              </label>
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
                        onClick={() => onSubmitIssue(repo, issue, githubToken)}
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
