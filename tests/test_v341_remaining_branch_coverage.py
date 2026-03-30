"""Tests for remaining branch partials in non-server modules (v341).

Covers four branch gaps that the coverage report still flags:

- ``github.py:820→822`` — ``_graphql()`` called without variables; the
  ``if variables:`` false-branch means ``payload`` lacks a ``"variables"`` key.
  A regression here would silently inject ``None`` into the GraphQL request body.

- ``e2e.py:224→239`` — ``pr_number`` is set but ``dry_run=True``; the
  ``if not dry_run:`` false-branch means the hand creates a fresh branch
  instead of resuming the PR's head.  A regression could cause a dry-run to
  mutate the live PR branch.

- ``cli/base.py:1535`` — ``_poll_ci_checks`` deadline exceeded between the
  ``while`` guard and the inner ``wait <= 0`` check.  Exercises the ``break``
  path that exits the poll loop without sleeping.

- ``cli/base.py:1719-1727`` — ``_ci_fix_loop`` overall loop-level timeout
  (``time.monotonic() > loop_deadline``).  Verifies the EXHAUSTED status and
  timeout message.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ===================================================================
# _graphql without variables (github.py:820→822)
# ===================================================================


class TestGraphqlWithoutVariables:
    """_graphql() should omit the 'variables' key when none are provided."""

    @pytest.fixture(autouse=True)
    def _fake_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake_token_for_tests")

    @pytest.fixture()
    def client(self):
        from helping_hands.lib.github import GitHubClient

        with patch("helping_hands.lib.github.Github"):
            return GitHubClient()

    def test_graphql_without_variables_omits_key(self, client) -> None:
        """When variables is None, the request body must not contain 'variables'."""
        captured_bodies: list[bytes] = []

        def mock_urlopen(req):
            captured_bodies.append(req.data)
            resp = MagicMock()
            resp.read.return_value = json.dumps(
                {"data": {"viewer": {"login": "test"}}}
            ).encode()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch("helping_hands.lib.github.urllib.request.urlopen", mock_urlopen):
            result = client._graphql("{ viewer { login } }")

        assert result == {"viewer": {"login": "test"}}
        body = json.loads(captured_bodies[0])
        assert "variables" not in body
        assert body["query"] == "{ viewer { login } }"

    def test_graphql_with_variables_includes_key(self, client) -> None:
        """When variables are provided, the request body must include them."""
        captured_bodies: list[bytes] = []

        def mock_urlopen(req):
            captured_bodies.append(req.data)
            resp = MagicMock()
            resp.read.return_value = json.dumps({"data": {"node": None}}).encode()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch("helping_hands.lib.github.urllib.request.urlopen", mock_urlopen):
            client._graphql("query($id: ID!) { node(id: $id) { id } }", {"id": "123"})

        body = json.loads(captured_bodies[0])
        assert body["variables"] == {"id": "123"}


# ===================================================================
# E2E dry_run + pr_number (e2e.py:224→239)
# ===================================================================


class TestE2EDryRunWithPrNumber:
    """dry_run=True with pr_number set should NOT resume the PR's head branch."""

    def test_dry_run_with_pr_number_creates_fresh_branch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)

        from helping_hands.lib.config import Config
        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        hand = E2EHand(config=Config(repo="owner/repo", model="test"), repo_index=None)

        gh = MagicMock()
        gh.default_branch.return_value = "main"
        gh.current_branch.return_value = "main"
        gh.clone.return_value = Path("/tmp/cloned")
        gh.get_pr.return_value = {
            "base": "develop",
            "head": "existing-feature-branch",
            "url": "https://github.com/owner/repo/pull/77",
        }
        gh.__enter__ = MagicMock(return_value=gh)
        gh.__exit__ = MagicMock(return_value=False)

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            result = hand.run(
                "test prompt",
                hand_uuid="uuid-drypr",
                pr_number=77,
                dry_run=True,
            )

        # Should get PR info but NOT resume the PR branch
        gh.get_pr.assert_called_once_with("owner/repo", 77)
        # resumed_pr should be False because dry_run=True
        assert result.metadata["resumed_pr"] == "false"
        assert result.metadata["dry_run"] == "true"
        # Should create a fresh branch, not fetch/switch to the PR's head
        gh.create_branch.assert_called_once()
        gh.fetch_branch.assert_not_called()
        gh.switch_branch.assert_not_called()
        # Base branch taken from PR info
        assert result.metadata["base_branch"] == "develop"


# ===================================================================
# _poll_ci_checks deadline break (cli/base.py:1535)
# ===================================================================


class TestPollCiChecksDeadlineBreak:
    """Exercise the 'wait <= 0' break path inside _poll_ci_checks."""

    def test_deadline_exceeded_between_poll_and_sleep(self) -> None:
        """When remaining time drops to 0 after get_check_runs, loop breaks."""
        from helping_hands.lib.hands.v1.hand.cli.base import (
            CIConclusion,
            _TwoPhaseCLIHand,
        )

        class _Stub(_TwoPhaseCLIHand):
            _CLI_LABEL = "stub"
            _BACKEND_NAME = "stub-poll"

            def __init__(self) -> None:
                self._interrupt_event = MagicMock()
                self._interrupt_event.is_set.return_value = False
                self._active_process = None
                self._ci_fix_mode = False
                self.fix_ci = False
                self.ci_check_wait_minutes = 0.001
                self.ci_max_retries = 1
                self.repo_index = MagicMock()
                self.config = MagicMock()
                self.config.verbose = False
                self.auto_pr = True

        stub = _Stub()
        mock_gh = MagicMock()

        # Always return pending
        mock_gh.get_check_runs.return_value = {
            "conclusion": CIConclusion.PENDING,
            "total_count": 1,
        }

        async def _emit(chunk: str) -> None:
            pass

        # Patch the module-level `time` object (not the global one) so asyncio
        # keeps its own real reference.  Also patch asyncio.sleep to a no-op.
        #
        # Sequence:
        # 1) deadline calc (line 1526): monotonic() → 100.0
        #    deadline = 100.0 + (100.0 - grace_period)  ≈ 200.0 - tiny
        # 2) while guard (line 1527): monotonic() → 100.0  (enters loop)
        # 3) remaining calc (line 1532): monotonic() → 200.1  (remaining < 0 → break)
        mock_time = MagicMock()
        mock_time.monotonic.side_effect = [100.0, 100.0, 200.1]

        with (
            patch("helping_hands.lib.hands.v1.hand.cli.base.time", mock_time),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = asyncio.run(
                stub._poll_ci_checks(
                    gh=mock_gh,
                    repo="owner/repo",
                    ref="abc123",
                    emit=_emit,
                    initial_wait=0.001,
                    max_poll_seconds=100.0,
                )
            )

        # Polled once in loop, once after break (line 1543)
        assert mock_gh.get_check_runs.call_count == 2
        assert result["conclusion"] == CIConclusion.PENDING


# ===================================================================
# _ci_fix_loop loop-level timeout (cli/base.py:1719-1727)
# ===================================================================


class TestCiFixLoopTimeout:
    """Exercise the loop_deadline timeout branch in _ci_fix_loop."""

    def test_loop_timeout_sets_exhausted_status(self) -> None:
        """When loop_deadline is exceeded, status is EXHAUSTED with message."""
        from helping_hands.lib.hands.v1.hand.cli.base import (
            CIFixStatus,
            _TwoPhaseCLIHand,
        )

        class _Stub(_TwoPhaseCLIHand):
            _CLI_LABEL = "stub"
            _BACKEND_NAME = "stub-timeout"

            def __init__(self) -> None:
                self._interrupt_event = MagicMock()
                self._interrupt_event.is_set.return_value = False
                self._active_process = None
                self._ci_fix_mode = False
                self.fix_ci = True
                self.ci_check_wait_minutes = 0.001
                self.ci_max_retries = 3
                self.repo_index = MagicMock()
                self.repo_index.root.resolve.return_value = "/fake/repo"
                self.config = MagicMock()
                self.config.model = "test-model"
                self.config.verbose = False
                self.config.github_token = None
                self.auto_pr = True

        stub = _Stub()
        emit, chunks = _collecting_emit_pair()

        metadata: dict[str, str] = {
            "pr_status": "created",
            "pr_commit": "abc123",
            "pr_branch": "fix/branch",
        }

        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        # Patch module-level time object:
        # 1st call (loop_deadline calc at line 1708): 100.0 → deadline = 1900
        # 2nd call (deadline check at line 1718): 2000.0 → > 1900 → timeout
        mock_time = MagicMock()
        mock_time.monotonic.side_effect = [100.0, 2000.0]

        with (
            patch("helping_hands.lib.hands.v1.hand.cli.base.time", mock_time),
            patch.object(
                _TwoPhaseCLIHand,
                "_github_repo_from_origin",
                return_value="owner/repo",
            ),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
        ):
            result = asyncio.run(
                stub._ci_fix_loop(
                    prompt="fix ci",
                    metadata=metadata,
                    emit=emit,
                )
            )

        assert result["ci_fix_status"] == CIFixStatus.EXHAUSTED
        assert any("timed out" in c.lower() for c in chunks)


def _collecting_emit_pair():
    """Return an async emitter and its collected chunks list."""
    chunks: list[str] = []

    async def _emit(chunk: str) -> None:
        chunks.append(chunk)

    return _emit, chunks
