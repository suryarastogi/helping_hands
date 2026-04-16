import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, describe, it, expect, vi } from "vitest";

import SubmitIssueOverlay from "./SubmitIssueOverlay";
import type { SubmitIssueOverlayProps } from "./SubmitIssueOverlay";

// ---------------------------------------------------------------------------
// Mock RepoSuggestInput to keep tests focused on SubmitIssueOverlay behavior.
// ---------------------------------------------------------------------------
vi.mock("./RepoSuggestInput", () => ({
  default: ({ value, onChange, placeholder, ariaLabel, className, required }: {
    value: string;
    onChange: (val: string) => void;
    placeholder?: string;
    ariaLabel?: string;
    required?: boolean;
    className?: string;
  }) => (
    <input
      data-testid="repo-suggest-input"
      className={className}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={ariaLabel}
      required={required}
    />
  ),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  try {
    window.localStorage.clear();
  } catch {
    /* ignore */
  }
});

function makeProps(overrides: Partial<SubmitIssueOverlayProps> = {}): SubmitIssueOverlayProps {
  return {
    recentRepos: [],
    serverHasGithubToken: true,
    defaultRepo: "",
    onSubmitIssue: vi.fn(),
    onClose: vi.fn(),
    ...overrides,
  };
}

describe("SubmitIssueOverlay draft persistence", () => {
  it("persists the repo input to localStorage on change", () => {
    render(<SubmitIssueOverlay {...makeProps()} />);
    const repoInput = screen.getByTestId("repo-suggest-input") as HTMLInputElement;
    fireEvent.change(repoInput, { target: { value: "owner/cool-repo" } });
    expect(window.localStorage.getItem("hh_submit_issue_repo_draft")).toBe(
      "owner/cool-repo",
    );
  });

  it("hydrates the repo input from the persisted draft", () => {
    window.localStorage.setItem("hh_submit_issue_repo_draft", "persisted/repo");
    render(<SubmitIssueOverlay {...makeProps({ defaultRepo: "other/repo" })} />);
    const repoInput = screen.getByTestId("repo-suggest-input") as HTMLInputElement;
    expect(repoInput.value).toBe("persisted/repo");
  });

  it("falls back to defaultRepo when no draft is persisted", () => {
    render(<SubmitIssueOverlay {...makeProps({ defaultRepo: "fallback/repo" })} />);
    const repoInput = screen.getByTestId("repo-suggest-input") as HTMLInputElement;
    expect(repoInput.value).toBe("fallback/repo");
  });
});
