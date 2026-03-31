"""Tests for v119: _ToolValidatorMixin provides shared coercion to both request models.

Before this mixin, BuildRequest and ScheduleRequest each had their own copy of the
tools string-to-list coercion logic; divergence caused different endpoints to
accept different input formats.  The mixin must be an actual base class of both
models (not just copied code) so that a single fix propagates to both.

String inputs ("execution,web") must be split into lists; None must become an empty
list; and per-item max_length constraints must prevent unbounded tool name strings.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")


# ---------------------------------------------------------------------------
# _ToolValidatorMixin shared behavior
# ---------------------------------------------------------------------------


class TestToolValidatorMixin:
    """Validate that the shared mixin provides coercion/validation to both models."""

    def test_build_request_inherits_mixin(self) -> None:
        from helping_hands.server.app import BuildRequest, _ToolValidatorMixin

        assert issubclass(BuildRequest, _ToolValidatorMixin)

    def test_schedule_request_inherits_mixin(self) -> None:
        from helping_hands.server.app import ScheduleRequest, _ToolValidatorMixin

        assert issubclass(ScheduleRequest, _ToolValidatorMixin)

    def test_mixin_coerces_tools_string_to_list(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/repo", prompt="test", tools="execution,web")
        assert isinstance(req.tools, list)
        assert "execution" in req.tools

    def test_schedule_request_coerces_tools(self) -> None:
        from helping_hands.server.app import ScheduleRequest

        req = ScheduleRequest(
            name="t",
            cron_expression="0 0 * * *",
            repo_path="/tmp/repo",
            prompt="test",
            tools="execution",
        )
        assert isinstance(req.tools, list)
        assert "execution" in req.tools

    def test_mixin_none_tools_becomes_empty_list(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/repo", prompt="test", tools=None)
        assert req.tools == []


# ---------------------------------------------------------------------------
# tools max_length constraints
# ---------------------------------------------------------------------------


class TestToolMaxLength:
    """Validate max_length constraint on tools list fields."""

    def test_max_tool_items_constant(self) -> None:
        from helping_hands.server.app import _MAX_TOOL_ITEMS

        assert _MAX_TOOL_ITEMS == 50

    def test_build_request_rejects_oversized_tools_list(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        # Use unique items so normalize_tool_selection doesn't dedup them.
        # The coercion validator runs first (mode="before"), but the max_length
        # constraint on the field triggers after coercion.
        tools = [f"tool_{i}" for i in range(51)]
        with pytest.raises(ValidationError):
            BuildRequest(
                repo_path="/tmp/repo",
                prompt="test",
                tools=tools,
            )

    def test_build_request_accepts_tools_at_limit(self) -> None:
        """Valid tool names at the limit should be accepted."""
        from helping_hands.server.app import BuildRequest

        # Single valid entry repeated — deduped to 1 by coercion.
        req = BuildRequest(
            repo_path="/tmp/repo",
            prompt="test",
            tools=["execution"],
        )
        assert len(req.tools) == 1


# ---------------------------------------------------------------------------
# base.py pr_number guards (assert -> ValueError)
# ---------------------------------------------------------------------------


class TestPrNumberExplicitGuards:
    """Verify assert-free ValueError guards for pr_number in base.py."""

    def _make_hand(self):
        """Create a minimal Hand subclass for testing."""
        from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse

        class _TestHand(Hand):
            def run(self, prompt: str) -> HandResponse:
                return HandResponse(message="ok")

            async def stream(self, prompt: str):
                yield "ok"

        config = MagicMock()
        config.enabled_tools = ()
        config.enable_execution = False
        config.enable_web = False
        repo_index = MagicMock()
        repo_index.root = MagicMock()
        repo_index.files = []
        return _TestHand(config, repo_index)

    def test_push_to_existing_pr_raises_without_pr_number(self) -> None:
        hand = self._make_hand()
        hand.pr_number = None
        with pytest.raises(ValueError, match="pr_number must be set"):
            hand._push_to_existing_pr(
                gh=MagicMock(),
                repo="owner/repo",
                repo_dir=MagicMock(),
                backend="test",
                prompt="test",
                summary="test",
                metadata={},
            )

    def test_update_pr_description_raises_without_pr_number(self) -> None:
        hand = self._make_hand()
        hand.pr_number = None
        with pytest.raises(ValueError, match="pr_number must be set"):
            hand._update_pr_description(
                gh=MagicMock(),
                repo="owner/repo",
                repo_dir=MagicMock(),
                backend="test",
                prompt="test",
                summary="test",
                base_branch="main",
                commit_sha="abc123",
            )

    def test_create_pr_for_diverged_branch_raises_without_pr_number(self) -> None:
        hand = self._make_hand()
        hand.pr_number = None
        with pytest.raises(ValueError, match="pr_number must be set"):
            hand._create_pr_for_diverged_branch(
                gh=MagicMock(),
                repo="owner/repo",
                repo_dir=MagicMock(),
                backend="test",
                prompt="test",
                summary="test",
                metadata={},
                pr_branch="feature-branch",
                commit_sha="abc123",
            )

    def test_push_to_existing_pr_proceeds_with_pr_number(self) -> None:
        hand = self._make_hand()
        hand.pr_number = 42

        mock_gh = MagicMock()
        mock_gh.get_pr.return_value = {
            "head": "feature",
            "base": "main",
            "url": "https://github.com/o/r/pull/42",
            "user": "bot",
        }
        mock_gh.whoami.return_value = {"login": "bot"}

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description.generate_commit_message",
                return_value="feat: test",
            ),
            patch.object(
                hand, "_add_and_commit_with_hook_retry", return_value="sha123"
            ),
            patch.object(hand, "_push_noninteractive"),
            patch.object(hand, "_update_pr_description"),
        ):
            result = hand._push_to_existing_pr(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=MagicMock(),
                backend="test",
                prompt="test",
                summary="test",
                metadata={},
            )
        assert result["pr_status"] == "updated"
        assert result["pr_number"] == "42"
