"""Tests for v118 server API field length limits.

Covers max_length constraints on BuildRequest and ScheduleRequest fields.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")


class TestBuildRequestFieldLengths:
    """Validate max_length constraints on BuildRequest fields."""

    def test_accepts_normal_repo_path(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/repo", prompt="do something")
        assert req.repo_path == "/tmp/repo"

    def test_rejects_oversized_repo_path(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="repo_path"):
            BuildRequest(repo_path="x" * 501, prompt="do something")

    def test_accepts_repo_path_at_limit(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="x" * 500, prompt="test")
        assert len(req.repo_path) == 500

    def test_rejects_oversized_prompt(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="prompt"):
            BuildRequest(repo_path="/tmp/repo", prompt="x" * 50_001)

    def test_accepts_prompt_at_limit(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/repo", prompt="x" * 50_000)
        assert len(req.prompt) == 50_000

    def test_rejects_oversized_model(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import BuildRequest

        with pytest.raises(ValidationError, match="model"):
            BuildRequest(repo_path="/tmp/repo", prompt="test", model="x" * 201)

    def test_accepts_model_at_limit(self) -> None:
        from helping_hands.server.app import BuildRequest

        req = BuildRequest(repo_path="/tmp/repo", prompt="test", model="x" * 200)
        assert len(req.model) == 200


class TestScheduleRequestFieldLengths:
    """Validate max_length constraints on ScheduleRequest fields."""

    def test_rejects_oversized_repo_path(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import ScheduleRequest

        with pytest.raises(ValidationError, match="repo_path"):
            ScheduleRequest(
                name="test",
                cron_expression="0 0 * * *",
                repo_path="x" * 501,
                prompt="test",
            )

    def test_rejects_oversized_prompt(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import ScheduleRequest

        with pytest.raises(ValidationError, match="prompt"):
            ScheduleRequest(
                name="test",
                cron_expression="0 0 * * *",
                repo_path="/tmp/repo",
                prompt="x" * 50_001,
            )

    def test_rejects_oversized_model(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import ScheduleRequest

        with pytest.raises(ValidationError, match="model"):
            ScheduleRequest(
                name="test",
                cron_expression="0 0 * * *",
                repo_path="/tmp/repo",
                prompt="test",
                model="x" * 201,
            )

    def test_rejects_oversized_cron_expression(self) -> None:
        from pydantic import ValidationError

        from helping_hands.server.app import ScheduleRequest

        with pytest.raises(ValidationError, match="cron_expression"):
            ScheduleRequest(
                name="test",
                cron_expression="x" * 101,
                repo_path="/tmp/repo",
                prompt="test",
            )

    def test_accepts_valid_schedule_request(self) -> None:
        from helping_hands.server.app import ScheduleRequest

        req = ScheduleRequest(
            name="nightly",
            cron_expression="0 0 * * *",
            repo_path="/tmp/repo",
            prompt="fix bugs",
        )
        assert req.name == "nightly"
        assert req.repo_path == "/tmp/repo"
