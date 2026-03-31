"""GitHub integration: auth, clone, branch, commit, and pull requests.

This module is designed to be used by agents (hands) as a tool.
It wraps PyGithub for the API and subprocess git for local operations.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import urllib.request
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from github import Auth, Github
from github.PullRequest import PullRequest
from github.Repository import Repository

from helping_hands.lib.github_url import (
    GITHUB_TOKEN_USER as _GITHUB_TOKEN_USER,
    redact_credentials as _redact_credentials,
    resolve_github_token as _resolve_github_token,
    validate_repo_spec as _validate_repo_spec,
)
from helping_hands.lib.validation import require_non_empty_string, require_positive_int

__all__ = ["CIConclusion", "GitHubClient", "PRResult"]

logger = logging.getLogger(__name__)

_DEFAULT_GIT_TIMEOUT = 300  # seconds
_MAX_GIT_TIMEOUT = 3600  # 1 hour hard cap
_VALID_PR_STATES = frozenset({"open", "closed", "all"})

_GIT_REF_PREFIX = "refs/heads/"
"""Git refspec prefix for branch references (e.g. ``refs/heads/main``)."""

_CHECK_RUN_STATUS_COMPLETED = "completed"
"""GitHub check-run ``status`` value indicating the run has finished."""


# --- CI conclusion enum -------------------------------------------------------


class CIConclusion(StrEnum):
    """Overall CI check-run conclusion returned by :meth:`GitHubClient.get_check_runs`.

    Being a :class:`StrEnum`, each member compares equal to its string value
    (e.g. ``CIConclusion.SUCCESS == "success"``), so serialised dicts remain
    human-readable and backward-compatible.
    """

    NO_CHECKS = "no_checks"
    """No CI check runs were found for the ref."""

    PENDING = "pending"
    """At least one check run has not completed yet."""

    SUCCESS = "success"
    """All check runs completed successfully."""

    FAILURE = "failure"
    """At least one check run failed."""

    MIXED = "mixed"
    """Check runs completed with a mix of conclusions (none failed)."""


CI_CONCLUSIONS_IN_PROGRESS = frozenset({CIConclusion.PENDING, CIConclusion.NO_CHECKS})
"""CI conclusion values indicating checks are not yet decisive."""

_CI_RUN_FAILURE_CONCLUSIONS = frozenset({"failure", "cancelled", "timed_out"})
"""Individual check-run ``conclusion`` values considered failures."""


def _git_timeout() -> int:
    """Return the git operation timeout in seconds.

    Reads ``HELPING_HANDS_GIT_TIMEOUT`` from the environment, falling back to
    :data:`_DEFAULT_GIT_TIMEOUT` (300 s).  Values above
    :data:`_MAX_GIT_TIMEOUT` (3600 s) are capped with a warning.
    """
    raw = os.environ.get("HELPING_HANDS_GIT_TIMEOUT", "")
    if raw.strip():
        try:
            value = int(raw)
            if value <= 0:
                logger.warning(
                    "HELPING_HANDS_GIT_TIMEOUT must be positive, using default"
                )
            elif value > _MAX_GIT_TIMEOUT:
                logger.warning(
                    "HELPING_HANDS_GIT_TIMEOUT=%d exceeds max %d, capping",
                    value,
                    _MAX_GIT_TIMEOUT,
                )
                return _MAX_GIT_TIMEOUT
            else:
                return value
        except ValueError:
            logger.warning(
                "HELPING_HANDS_GIT_TIMEOUT=%r is not an integer, using default",
                raw,
            )
    return _DEFAULT_GIT_TIMEOUT


def _validate_full_name(full_name: str) -> None:
    """Validate that *full_name* matches the ``owner/repo`` format.

    Delegates to :func:`github_url.validate_repo_spec` for the structural
    check, then adds a whitespace guard specific to API-facing full names.

    Raises:
        ValueError: If the string is empty, missing a ``/``, has empty segments,
            or contains whitespace.
    """
    require_non_empty_string(full_name, "full_name")
    if " " in full_name or "\t" in full_name:
        raise ValueError(f"full_name must not contain whitespace: {full_name!r}")
    _validate_repo_spec(full_name)


def _validate_branch_name(branch_name: str) -> None:
    """Validate that *branch_name* is a non-empty string.

    Raises:
        ValueError: If the string is empty or whitespace-only.
    """
    require_non_empty_string(branch_name, "branch_name")


def _redact_sensitive(text: str) -> str:
    """Redact token-bearing GitHub URLs in logs/errors."""
    return _redact_credentials(text)


@dataclass
class PRResult:
    """Result of creating a pull request.

    Attributes:
        number: PR number on GitHub.
        url: Full HTML URL of the pull request.
        title: PR title as submitted.
        head: Source branch name.
        base: Target branch name.
    """

    number: int
    url: str
    title: str
    head: str
    base: str


@dataclass
class GitHubClient:
    """Authenticated GitHub client for repo operations.

    Supports token auth (PAT or fine-grained) and GitHub App installation
    tokens. The token is read from the ``token`` field, or falls back to
    the ``GITHUB_TOKEN`` / ``GH_TOKEN`` environment variable.
    """

    token: str = ""
    _gh: Github = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Resolve the GitHub token and initialise the PyGithub client.

        The token is resolved from the ``token`` field, then
        ``GITHUB_TOKEN``, then ``GH_TOKEN`` environment variable.

        Raises:
            ValueError: If no token is available from any source.
        """
        resolved = _resolve_github_token(self.token)
        if not resolved:
            msg = (
                "No GitHub token provided. Set GITHUB_TOKEN or GH_TOKEN, "
                "or pass token= explicitly."
            )
            raise ValueError(msg)
        self.token = resolved
        self._gh = Github(auth=Auth.Token(self.token))

    # ------------------------------------------------------------------
    # Auth / identity
    # ------------------------------------------------------------------

    def whoami(self) -> dict[str, Any]:
        """Return identity information for the authenticated GitHub user.

        Returns:
            A dict with keys ``login`` (str), ``name`` (str or None),
            and ``url`` (str) pointing to the user's GitHub profile.
        """
        user = self._gh.get_user()
        return {"login": user.login, "name": user.name, "url": user.html_url}

    # ------------------------------------------------------------------
    # Repository
    # ------------------------------------------------------------------

    def get_repo(self, full_name: str) -> Repository:
        """Get a repository by owner/name (e.g. ``"suryarastogi/helping_hands"``)."""
        _validate_full_name(full_name)
        return self._gh.get_repo(full_name)

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------

    def clone(
        self,
        full_name: str,
        dest: Path | str,
        *,
        branch: str | None = None,
        depth: int | None = 1,
    ) -> Path:
        """Clone a repo to *dest* using the authenticated token for HTTPS.

        Args:
            full_name: ``owner/repo`` string.
            dest: Local directory to clone into. Created if it doesn't exist.
            branch: Optional branch to check out.
            depth: Shallow clone depth. ``None`` for full history.

        Returns:
            Path to the cloned repository.
        """
        _validate_full_name(full_name)
        dest = Path(dest)
        if depth is not None:
            require_positive_int(depth, "depth")
        url = f"https://{_GITHUB_TOKEN_USER}:{self.token}@github.com/{full_name}.git"
        cmd: list[str] = ["git", "clone"]
        if depth is not None:
            cmd += ["--depth", str(depth)]
        if branch:
            cmd += ["--branch", branch]
        cmd += [url, str(dest)]
        _run_git(cmd)
        logger.info("Cloned %s → %s", full_name, dest)
        return dest

    # ------------------------------------------------------------------
    # Branch
    # ------------------------------------------------------------------

    @staticmethod
    def create_branch(repo_path: Path | str, branch_name: str) -> None:
        """Create and switch to a new branch in a local repo."""
        _validate_branch_name(branch_name)
        _run_git(["git", "checkout", "-b", branch_name], cwd=repo_path)

    @staticmethod
    def switch_branch(repo_path: Path | str, branch_name: str) -> None:
        """Switch to an existing branch."""
        _validate_branch_name(branch_name)
        _run_git(["git", "checkout", branch_name], cwd=repo_path)

    @staticmethod
    def fetch_branch(
        repo_path: Path | str,
        branch_name: str,
        *,
        remote: str = "origin",
    ) -> None:
        """Fetch a remote branch into a matching local branch name."""
        _validate_branch_name(branch_name)
        _run_git(
            [
                "git",
                "fetch",
                remote,
                f"{_GIT_REF_PREFIX}{branch_name}:{_GIT_REF_PREFIX}{branch_name}",
            ],
            cwd=repo_path,
        )

    @staticmethod
    def pull(
        repo_path: Path | str,
        *,
        remote: str = "origin",
        branch: str | None = None,
    ) -> None:
        """Pull latest changes from remote into the current branch."""
        cmd = ["git", "pull", remote]
        if branch:
            cmd.append(branch)
        _run_git(cmd, cwd=repo_path)

    @staticmethod
    def current_branch(repo_path: Path | str) -> str:
        """Return the name of the current branch."""
        result = _run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        return result.stdout.strip()

    # ------------------------------------------------------------------
    # Commit
    # ------------------------------------------------------------------

    @staticmethod
    def add_and_commit(
        repo_path: Path | str,
        message: str,
        *,
        paths: list[str] | None = None,
    ) -> str:
        """Stage files and commit. Returns the commit SHA.

        Args:
            repo_path: Local repo directory.
            message: Commit message.
            paths: Specific paths to ``git add``. Defaults to ``["."]`` (all).

        Returns:
            The short SHA of the new commit.
        """
        require_non_empty_string(message, "commit message")
        targets = paths or ["."]
        _run_git(["git", "add", *targets], cwd=repo_path)
        _run_git(["git", "commit", "-m", message], cwd=repo_path)
        result = _run_git(["git", "rev-parse", "--short", "HEAD"], cwd=repo_path)
        return result.stdout.strip()

    @staticmethod
    def set_local_identity(
        repo_path: Path | str,
        *,
        name: str,
        email: str,
    ) -> None:
        """Set git author identity in local repo config."""
        require_non_empty_string(name, "name")
        require_non_empty_string(email, "email")
        _run_git(["git", "config", "user.name", name], cwd=repo_path)
        _run_git(["git", "config", "user.email", email], cwd=repo_path)

    # ------------------------------------------------------------------
    # Push
    # ------------------------------------------------------------------

    def push(
        self,
        repo_path: Path | str,
        *,
        remote: str = "origin",
        branch: str | None = None,
        set_upstream: bool = True,
    ) -> None:
        """Push the current branch to the remote.

        Args:
            repo_path: Local repo directory.
            remote: Remote name.
            branch: Branch to push. Defaults to current branch.
            set_upstream: If True, set the upstream tracking ref.
        """
        branch = branch or self.current_branch(repo_path)
        cmd = ["git", "push"]
        if set_upstream:
            cmd += ["-u", remote, branch]
        else:
            cmd += [remote, branch]
        _run_git(cmd, cwd=repo_path)

    # ------------------------------------------------------------------
    # Pull request
    # ------------------------------------------------------------------

    def create_pr(
        self,
        full_name: str,
        *,
        title: str,
        body: str = "",
        head: str,
        base: str = "main",
        draft: bool = False,
    ) -> PRResult:
        """Create a pull request on GitHub.

        Args:
            full_name: ``owner/repo`` string.
            title: PR title.
            body: PR body (markdown).
            head: Source branch name.
            base: Target branch name.
            draft: Whether to create as a draft PR.

        Returns:
            A ``PRResult`` with the PR number, URL, title, head, and base.

        Raises:
            ValueError: If *title* is empty/whitespace, or *head*/*base* are
                invalid branch names.
        """
        require_non_empty_string(title, "title")
        _validate_branch_name(head)
        _validate_branch_name(base)
        repo = self.get_repo(full_name)
        pr: PullRequest = repo.create_pull(
            title=title, body=body, head=head, base=base, draft=draft
        )
        logger.info("Created PR #%d: %s", pr.number, pr.html_url)
        return PRResult(
            number=pr.number,
            url=pr.html_url,
            title=pr.title,
            head=head,
            base=base,
        )

    # ------------------------------------------------------------------
    # PR helpers
    # ------------------------------------------------------------------

    def list_prs(
        self,
        full_name: str,
        *,
        state: str = "open",
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """List pull requests for a repo.

        Args:
            full_name: ``owner/repo`` string.
            state: ``"open"``, ``"closed"``, or ``"all"``.
            limit: Maximum number of PRs to return.
        """
        require_positive_int(limit, "limit")
        if state not in _VALID_PR_STATES:
            raise ValueError(
                f"state must be one of {sorted(_VALID_PR_STATES)}, got {state!r}"
            )
        repo = self.get_repo(full_name)
        prs: list[PullRequest] = list(
            repo.get_pulls(state=state, sort="created", direction="desc")
        )[:limit]
        return [
            {
                "number": pr.number,
                "title": pr.title,
                "url": pr.html_url,
                "state": pr.state,
                "head": pr.head.ref,
                "base": pr.base.ref,
            }
            for pr in prs
        ]

    def get_pr(self, full_name: str, number: int) -> dict[str, Any]:
        """Get details of a single pull request.

        Args:
            full_name: ``owner/repo`` string.
            number: PR number (must be positive).

        Returns:
            A dict with keys ``number``, ``title``, ``body``, ``url``,
            ``state``, ``head``, ``base``, ``mergeable``, ``merged``,
            and ``user``.

        Raises:
            ValueError: If *number* is not positive.
        """
        require_positive_int(number, "PR number")
        repo = self.get_repo(full_name)
        pr = repo.get_pull(number)
        return {
            "number": pr.number,
            "title": pr.title,
            "body": pr.body,
            "url": pr.html_url,
            "state": pr.state,
            "head": pr.head.ref,
            "base": pr.base.ref,
            "mergeable": pr.mergeable,
            "merged": pr.merged,
            "user": pr.user.login if pr.user else "",
        }

    def default_branch(self, full_name: str) -> str:
        """Return the repository's default branch name.

        Args:
            full_name: ``owner/repo`` string.

        Returns:
            The default branch name (e.g. ``"main"`` or ``"master"``).
        """
        repo = self.get_repo(full_name)
        return str(repo.default_branch)

    def update_pr_body(self, full_name: str, number: int, *, body: str) -> None:
        """Update the body/description of an existing pull request.

        Args:
            full_name: ``owner/repo`` string.
            number: PR number (must be positive).
            body: New Markdown body text for the pull request.

        Raises:
            ValueError: If *number* is not positive.
        """
        require_positive_int(number, "PR number")
        repo = self.get_repo(full_name)
        pr = repo.get_pull(number)
        pr.edit(body=body)

    def update_pr(
        self,
        full_name: str,
        number: int,
        *,
        title: str | None = None,
        body: str | None = None,
    ) -> None:
        """Update the title and/or body of an existing pull request.

        Args:
            full_name: ``owner/repo`` string.
            number: PR number (must be positive).
            title: New PR title, or ``None`` to leave unchanged.
            body: New Markdown body text, or ``None`` to leave unchanged.

        Raises:
            ValueError: If *number* is not positive or both *title* and
                *body* are ``None``.
        """
        require_positive_int(number, "PR number")
        if title is None and body is None:
            return
        from github import NotSet

        repo = self.get_repo(full_name)
        pr = repo.get_pull(number)
        pr.edit(
            title=title if title is not None else NotSet,
            body=body if body is not None else NotSet,
        )

    def get_check_runs(
        self,
        full_name: str,
        ref: str,
    ) -> dict[str, Any]:
        """Get CI check runs for a commit SHA or branch reference.

        Args:
            full_name: ``owner/repo`` string.
            ref: Commit SHA, branch name, or tag.

        Returns:
            A dict with ``ref``, ``total_count``, ``conclusion`` (overall),
            and ``check_runs`` (list of individual run summaries).

        Raises:
            ValueError: If *ref* is empty or whitespace-only.
        """
        require_non_empty_string(ref, "ref")
        repo = self.get_repo(full_name)
        commit = repo.get_commit(ref)
        runs = commit.get_check_runs()

        check_list: list[dict[str, Any]] = []
        for run in runs:
            check_list.append(
                {
                    "name": run.name,
                    "status": run.status,
                    "conclusion": run.conclusion,
                    "html_url": run.html_url,
                    "started_at": (
                        run.started_at.isoformat() if run.started_at else None
                    ),
                    "completed_at": (
                        run.completed_at.isoformat() if run.completed_at else None
                    ),
                }
            )

        if not check_list:
            overall: str = CIConclusion.NO_CHECKS
        elif any(r["status"] != _CHECK_RUN_STATUS_COMPLETED for r in check_list):
            overall = CIConclusion.PENDING
        elif all(r["conclusion"] == CIConclusion.SUCCESS for r in check_list):
            overall = CIConclusion.SUCCESS
        elif any(r["conclusion"] == CIConclusion.FAILURE for r in check_list):
            overall = CIConclusion.FAILURE
        else:
            overall = CIConclusion.MIXED

        return {
            "ref": ref,
            "total_count": len(check_list),
            "conclusion": overall,
            "check_runs": check_list,
        }

    def upsert_pr_comment(
        self,
        full_name: str,
        number: int,
        *,
        body: str,
        marker: str = "<!-- helping_hands:status -->",
    ) -> int:
        """Create or update a marker-tagged PR comment.

        If a comment containing ``marker`` already exists, it is edited in place.
        Otherwise, a new comment is created.

        Raises:
            ValueError: If *number* is not positive or *body* is empty/whitespace.
        """
        require_positive_int(number, "PR number")
        require_non_empty_string(body, "comment body")
        repo = self.get_repo(full_name)
        issue = repo.get_issue(number=number)
        comment_body = body.rstrip()
        if marker and marker not in comment_body:
            comment_body = f"{comment_body}\n\n{marker}"

        for comment in issue.get_comments():
            existing = comment.body or ""
            if marker and marker in existing:
                comment.edit(comment_body)
                return int(comment.id)

        created = issue.create_comment(comment_body)
        return int(created.id)

    # ------------------------------------------------------------------
    # Issue helpers
    # ------------------------------------------------------------------

    def get_issue(self, full_name: str, number: int) -> dict[str, Any]:
        """Get details of a single issue.

        Args:
            full_name: ``owner/repo`` string.
            number: Issue number (must be positive).

        Returns:
            A dict with keys ``number``, ``title``, ``body``, ``url``,
            ``state``, ``labels``, and ``user``.

        Raises:
            ValueError: If *number* is not positive.
        """
        require_positive_int(number, "issue number")
        repo = self.get_repo(full_name)
        issue = repo.get_issue(number=number)
        return {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body or "",
            "url": issue.html_url,
            "state": issue.state,
            "labels": [label.name for label in issue.labels],
            "user": issue.user.login if issue.user else "",
        }

    def create_issue_comment(
        self,
        full_name: str,
        number: int,
        *,
        body: str,
    ) -> int:
        """Post a comment on a GitHub issue.

        Args:
            full_name: ``owner/repo`` string.
            number: Issue number (must be positive).
            body: Comment body (markdown).

        Returns:
            The ID of the created comment.

        Raises:
            ValueError: If *number* is not positive or *body* is
                empty/whitespace.
        """
        require_positive_int(number, "issue number")
        require_non_empty_string(body, "comment body")
        repo = self.get_repo(full_name)
        issue = repo.get_issue(number=number)
        comment = issue.create_comment(body)
        return int(comment.id)

    def create_issue(
        self,
        full_name: str,
        *,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new issue on a GitHub repository.

        Args:
            full_name: ``owner/repo`` string.
            title: Issue title (must not be empty).
            body: Issue body (markdown). Defaults to empty string.
            labels: Optional list of label names to apply.

        Returns:
            A dict with keys ``number``, ``title``, ``body``, ``url``,
            ``state``, and ``labels``.

        Raises:
            ValueError: If *title* is empty/whitespace.
        """
        require_non_empty_string(title, "issue title")
        repo = self.get_repo(full_name)
        kwargs: dict[str, Any] = {"title": title, "body": body}
        if labels:
            kwargs["labels"] = labels
        issue = repo.create_issue(**kwargs)
        return {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body or "",
            "url": issue.html_url,
            "state": issue.state,
            "labels": [label.name for label in issue.labels],
        }

    # ------------------------------------------------------------------
    # Issue labels
    # ------------------------------------------------------------------

    def add_issue_labels(
        self,
        full_name: str,
        number: int,
        *,
        labels: list[str],
    ) -> list[str]:
        """Add labels to a GitHub issue.

        Creates labels that don't yet exist on the repository (with a
        default grey colour).  Labels already present on the issue are
        silently kept.

        Args:
            full_name: ``owner/repo`` string.
            number: Issue number (must be positive).
            labels: List of label names to add (must not be empty).

        Returns:
            The full list of label names now on the issue.

        Raises:
            ValueError: If *number* is not positive or *labels* is empty.
        """
        require_positive_int(number, "issue number")
        if not labels:
            msg = "labels list must not be empty"
            raise ValueError(msg)
        repo = self.get_repo(full_name)
        issue = repo.get_issue(number=number)
        # Ensure all requested labels exist on the repo.
        existing_labels = {lbl.name for lbl in repo.get_labels()}
        for name in labels:
            if name not in existing_labels:
                repo.create_label(name=name, color="ededed")
        issue.add_to_labels(*labels)
        return [lbl.name for lbl in issue.labels]

    def remove_issue_label(
        self,
        full_name: str,
        number: int,
        *,
        label: str,
    ) -> None:
        """Remove a single label from a GitHub issue.

        Does nothing if the label is not present on the issue.

        Args:
            full_name: ``owner/repo`` string.
            number: Issue number (must be positive).
            label: Label name to remove.

        Raises:
            ValueError: If *number* is not positive or *label* is
                empty/whitespace.
        """
        require_positive_int(number, "issue number")
        require_non_empty_string(label, "label")
        repo = self.get_repo(full_name)
        issue = repo.get_issue(number=number)
        try:
            issue.remove_from_labels(label)
        except Exception:
            # Label may not be on the issue — silently ignore.
            logger.debug(
                "Could not remove label %r from %s#%d",
                label,
                full_name,
                number,
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # GitHub Projects v2
    # ------------------------------------------------------------------

    _GRAPHQL_URL = "https://api.github.com/graphql"

    _PROJECT_URL_RE = re.compile(
        r"https?://github\.com/"
        r"(?P<type>orgs|users)/(?P<owner>[^/]+)"
        r"/projects/(?P<number>\d+)"
    )
    """Regex matching GitHub Project v2 URLs.

    Supports both organisation and user projects:
    - ``https://github.com/orgs/myorg/projects/5``
    - ``https://github.com/users/myuser/projects/3``
    """

    def _graphql(self, query: str, variables: dict[str, Any] | None = None) -> Any:
        """Execute a GitHub GraphQL query and return the ``data`` payload.

        Args:
            query: GraphQL query or mutation string.
            variables: Optional variables dict for the query.

        Returns:
            The ``data`` value from the GraphQL response.

        Raises:
            RuntimeError: If the response contains ``errors``.
        """
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            self._GRAPHQL_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
        if result.get("errors"):
            msgs = "; ".join(e.get("message", "") for e in result["errors"])
            raise RuntimeError(f"GraphQL error: {msgs}")
        return result.get("data")

    @staticmethod
    def parse_project_url(url: str) -> tuple[str, str, int]:
        """Parse a GitHub Project v2 URL into ``(owner_type, owner, number)``.

        Args:
            url: Full URL like ``https://github.com/orgs/myorg/projects/5``.

        Returns:
            A tuple of (``"organization"`` or ``"user"``, owner name, project number).

        Raises:
            ValueError: If the URL does not match the expected pattern.
        """
        require_non_empty_string(url, "project URL")
        m = GitHubClient._PROJECT_URL_RE.match(url.strip())
        if not m:
            raise ValueError(
                f"Invalid GitHub Project URL: {url!r}. "
                "Expected format: https://github.com/orgs/<owner>/projects/<number> "
                "or https://github.com/users/<owner>/projects/<number>"
            )
        owner_type = "organization" if m.group("type") == "orgs" else "user"
        return owner_type, m.group("owner"), int(m.group("number"))

    def add_to_project_v2(
        self,
        project_url: str,
        *,
        content_id: str | None = None,
        full_name: str | None = None,
        issue_number: int | None = None,
    ) -> str:
        """Add an issue or PR to a GitHub Projects v2 board.

        Either provide ``content_id`` directly (the GraphQL node ID of the
        issue or PR), or provide ``full_name`` and ``issue_number`` to have it
        resolved automatically.

        Args:
            project_url: Full GitHub Project URL (org or user project).
            content_id: GraphQL node ID of the issue/PR to add.
            full_name: ``owner/repo`` string (used with *issue_number*).
            issue_number: Issue or PR number (used with *full_name*).

        Returns:
            The project item ID of the added item.

        Raises:
            ValueError: If neither *content_id* nor (*full_name* +
                *issue_number*) are provided, or the URL is invalid.
            RuntimeError: If the GraphQL call fails.
        """
        require_non_empty_string(project_url, "project URL")

        # Resolve the content node ID if not provided directly.
        if not content_id:
            if not full_name or not issue_number:
                raise ValueError(
                    "Either content_id or both full_name and issue_number are required"
                )
            data = self._graphql(
                """
                query($owner: String!, $repo: String!, $number: Int!) {
                  repository(owner: $owner, name: $repo) {
                    issueOrPullRequest(number: $number) {
                      ... on Issue { id }
                      ... on PullRequest { id }
                    }
                  }
                }
                """,
                variables={
                    "owner": full_name.split("/")[0],
                    "repo": full_name.split("/")[1],
                    "number": issue_number,
                },
            )
            node = (data or {}).get("repository", {}).get("issueOrPullRequest")
            if not node or "id" not in node:
                raise RuntimeError(
                    f"Could not resolve node ID for {full_name}#{issue_number}"
                )
            content_id = node["id"]

        # Resolve the project node ID from the URL.
        owner_type, owner, number = self.parse_project_url(project_url)
        if owner_type == "organization":
            query = """
            query($login: String!, $number: Int!) {
              organization(login: $login) {
                projectV2(number: $number) { id }
              }
            }
            """
            data = self._graphql(query, variables={"login": owner, "number": number})
            project_id = (
                (data or {}).get("organization", {}).get("projectV2", {}).get("id")
            )
        else:
            query = """
            query($login: String!, $number: Int!) {
              user(login: $login) {
                projectV2(number: $number) { id }
              }
            }
            """
            data = self._graphql(query, variables={"login": owner, "number": number})
            project_id = (data or {}).get("user", {}).get("projectV2", {}).get("id")

        if not project_id:
            raise RuntimeError(f"Could not resolve project ID for {project_url}")

        # Add the item to the project.
        mutation = """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item { id }
          }
        }
        """
        data = self._graphql(
            mutation,
            variables={"projectId": project_id, "contentId": content_id},
        )
        item_id = (
            (data or {}).get("addProjectV2ItemById", {}).get("item", {}).get("id", "")
        )
        logger.info("Added item to project %s (item_id=%s)", project_url, item_id)
        return item_id

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying GitHub connection."""
        self._gh.close()

    def __enter__(self) -> GitHubClient:
        """Enter the context manager, returning ``self``."""
        return self

    def __exit__(self, *_: Any) -> None:
        """Exit the context manager, closing the underlying connection."""
        self.close()


# ---------------------------------------------------------------------------
# Git subprocess helper
# ---------------------------------------------------------------------------


def _run_git(
    cmd: list[str],
    *,
    cwd: Path | str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a git command, raising on failure or timeout."""
    timeout = _git_timeout()
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        safe_cmd = " ".join(_redact_sensitive(part) for part in cmd)
        msg = f"git timed out after {timeout}s ({safe_cmd})"
        raise RuntimeError(msg) from None
    if result.returncode != 0:
        safe_cmd = " ".join(_redact_sensitive(part) for part in cmd)
        safe_stderr = _redact_sensitive(result.stderr.strip())
        msg = f"git failed ({safe_cmd}): {safe_stderr}"
        raise RuntimeError(msg)
    return result
