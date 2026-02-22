"""Live integration test for E2EHand against GitHub.

This test is opt-in and intended for CI with secrets configured.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand import E2EHand
from helping_hands.lib.repo import RepoIndex


def _integration_enabled() -> bool:
    return os.environ.get("HELPING_HANDS_RUN_E2E_INTEGRATION", "") == "1"


def _is_master_branch() -> bool:
    branch = (
        os.environ.get("GITHUB_REF_NAME")
        or os.environ.get("CI_COMMIT_BRANCH")
        or os.environ.get("BRANCH_NAME")
        or ""
    )
    return branch == "master"


def _is_primary_python() -> bool:
    return sys.version_info[:2] == (3, 13)


@pytest.mark.integration
def test_e2e_hand_updates_existing_pr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not _integration_enabled():
        pytest.skip("Set HELPING_HANDS_RUN_E2E_INTEGRATION=1 to run live E2E test.")

    if not (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")):
        pytest.skip("GITHUB_TOKEN or GH_TOKEN is required for live E2E test.")

    repo = os.environ.get("HELPING_HANDS_E2E_REPO", "suryarastogi/helping_hands")
    pr_number = int(os.environ.get("HELPING_HANDS_E2E_PR_NUMBER", "1"))
    should_push = _is_master_branch() and _is_primary_python()

    monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))

    hand = E2EHand(
        Config(repo=repo, model="default"),
        RepoIndex(root=tmp_path, files=[]),
    )
    response = hand.run(
        prompt=(
            "CI integration run: update PR on master with primary Python"
            if should_push
            else "CI integration run: dry-run on non-primary CI target"
        ),
        pr_number=pr_number,
        dry_run=not should_push,
    )

    assert response.metadata["backend"] == "e2e"
    assert response.metadata["repo"] == repo
    assert Path(response.metadata["workspace"]).exists()
    if should_push:
        assert response.metadata["dry_run"] == "false"
        assert response.metadata["pr_number"] == str(pr_number)
        assert response.metadata["resumed_pr"] == "true"
        assert response.metadata["pr_url"].endswith(f"/pull/{pr_number}")
    else:
        assert response.metadata["dry_run"] == "true"
        assert response.metadata["commit"] == ""
