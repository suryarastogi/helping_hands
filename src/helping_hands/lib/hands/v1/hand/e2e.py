"""End-to-end hand implementation for live repository/PR integration tests.

``E2EHand`` inherits the Hand interface but owns a concrete GitHub workflow
used by CLI ``--e2e`` and app worker task paths: clone, branch, edit, commit,
push, PR create/update, and status-comment refresh.
"""

from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse


class E2EHand(Hand):
    """End-to-end hand for live clone/edit/commit/push/PR integration.

    Supports both **new PR** and **resume existing PR** (``pr_number``)
    paths.  Uses a deterministic workspace layout
    ``{hand_uuid}/git/{repo}``.  In live mode, updates both the PR body
    and a marker-tagged status comment so reruns refresh existing state
    rather than creating drift.
    """

    def __init__(self, config: Any, repo_index: Any) -> None:
        super().__init__(config, repo_index)

    @staticmethod
    def _safe_repo_dir(repo: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", repo.strip("/"))

    @staticmethod
    def _work_base() -> Path:
        root = os.environ.get("HELPING_HANDS_WORK_ROOT", ".")
        return Path(root).expanduser()

    @staticmethod
    def _configured_base_branch() -> str:
        return os.environ.get("HELPING_HANDS_BASE_BRANCH", "").strip()

    @staticmethod
    def _build_e2e_pr_comment(
        *,
        hand_uuid: str,
        prompt: str,
        stamp_utc: str,
        commit_sha: str,
    ) -> str:
        # E2E is deterministic; production hands should provide AI-authored
        # PR summaries/comments when they own the PR workflow.
        return (
            "## helping_hands E2E update\n\n"
            f"- latest_updated_utc: `{stamp_utc}`\n"
            f"- hand_uuid: `{hand_uuid}`\n"
            f"- commit: `{commit_sha}`\n"
            f"- prompt: {prompt}\n"
        )

    @staticmethod
    def _build_e2e_pr_body(
        *,
        hand_uuid: str,
        prompt: str,
        stamp_utc: str,
        commit_sha: str,
    ) -> str:
        return (
            "Automated E2E validation PR.\n\n"
            f"- latest_updated_utc: `{stamp_utc}`\n"
            f"- hand_uuid: `{hand_uuid}`\n"
            f"- prompt: {prompt}\n"
            f"- commit: `{commit_sha}`\n"
        )

    def run(
        self,
        prompt: str,
        hand_uuid: str | None = None,
        pr_number: int | None = None,
        dry_run: bool = False,
    ) -> HandResponse:
        from helping_hands.lib.github import GitHubClient

        repo = self.config.repo.strip()
        if not repo:
            raise ValueError("E2EHand requires config.repo set to a GitHub owner/repo.")

        hand_uuid = hand_uuid or str(uuid4())
        safe_repo = self._safe_repo_dir(self.config.repo)
        hand_root = self._work_base() / hand_uuid
        repo_dir = hand_root / "git" / safe_repo
        repo_dir.parent.mkdir(parents=True, exist_ok=True)

        base_branch = self._configured_base_branch() or "main"
        branch = f"helping-hands/e2e-{hand_uuid[:8]}"
        e2e_file = "HELPING_HANDS_E2E.md"
        e2e_path = repo_dir / e2e_file

        with GitHubClient() as gh:
            pr_url = ""
            resumed_pr = False
            pr_info: dict[str, Any] | None = None
            clone_branch = base_branch
            if pr_number is not None:
                pr_info = gh.get_pr(repo, pr_number)
                base_branch = str(pr_info["base"])
                pr_url = str(pr_info["url"])
                clone_branch = base_branch
                if not dry_run:
                    branch = str(pr_info["head"])
                    resumed_pr = True
            elif not self._configured_base_branch():
                try:
                    base_branch = gh.default_branch(repo)
                    clone_branch = base_branch
                except Exception:
                    clone_branch = None

            gh.clone(repo, repo_dir, branch=clone_branch, depth=1)
            if clone_branch is None:
                detected = gh.current_branch(repo_dir)
                if detected:
                    base_branch = detected
            repo_dir.mkdir(parents=True, exist_ok=True)
            if resumed_pr:
                gh.fetch_branch(repo_dir, branch)
                gh.switch_branch(repo_dir, branch)
            else:
                gh.create_branch(repo_dir, branch)

            stamp = datetime.now(UTC).replace(microsecond=0).isoformat()
            e2e_path.write_text(
                (
                    "# helping_hands E2E marker\n\n"
                    f"- hand_uuid: `{hand_uuid}`\n"
                    f"- prompt: {prompt}\n"
                    f"- timestamp_utc: {stamp}\n"
                ),
                encoding="utf-8",
            )
            commit_sha = ""
            final_pr_number = pr_number
            if not dry_run:
                git_name = os.environ.get(
                    "HELPING_HANDS_GIT_USER_NAME", "helping-hands[bot]"
                )
                git_email = os.environ.get(
                    "HELPING_HANDS_GIT_USER_EMAIL",
                    "helping-hands-bot@users.noreply.github.com",
                )
                gh.set_local_identity(repo_dir, name=git_name, email=git_email)
                commit_sha = gh.add_and_commit(
                    repo_dir,
                    "test(e2e): minimal change from E2EHand",
                    paths=[e2e_file],
                )
                gh.push(repo_dir, branch=branch, set_upstream=True)
                pr_body = self._build_e2e_pr_body(
                    hand_uuid=hand_uuid,
                    prompt=prompt,
                    stamp_utc=stamp,
                    commit_sha=commit_sha,
                )
                if resumed_pr:
                    final_pr_number = pr_number
                else:
                    pr = gh.create_pr(
                        repo,
                        title="test(e2e): minimal edit by helping_hands",
                        body=pr_body,
                        head=branch,
                        base=base_branch,
                    )
                    pr_url = pr.url
                    final_pr_number = pr.number
                if final_pr_number is not None:
                    gh.update_pr_body(repo, final_pr_number, body=pr_body)
                    gh.upsert_pr_comment(
                        repo,
                        final_pr_number,
                        body=self._build_e2e_pr_comment(
                            hand_uuid=hand_uuid,
                            prompt=prompt,
                            stamp_utc=stamp,
                            commit_sha=commit_sha,
                        ),
                        marker="<!-- helping_hands:e2e-status -->",
                    )

        if dry_run:
            message = "E2EHand dry run complete. No push/PR performed."
        else:
            message = f"E2EHand complete. PR: {pr_url}"
        return HandResponse(
            message=message,
            metadata={
                "backend": "e2e",
                "model": self.config.model,
                "hand_uuid": hand_uuid,
                "hand_root": str(hand_root),
                "repo": repo,
                "workspace": str(repo_dir),
                "branch": branch,
                "base_branch": base_branch,
                "commit": commit_sha,
                "pr_number": "" if final_pr_number is None else str(final_pr_number),
                "pr_url": pr_url,
                "resumed_pr": str(resumed_pr).lower(),
                "dry_run": str(dry_run).lower(),
            },
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield self.run(prompt).message
