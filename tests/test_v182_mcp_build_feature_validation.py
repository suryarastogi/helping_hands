"""v182: MCP build_feature backend and max_iterations validation.

Tests cover:
- MCP build_feature backend validation against _SUPPORTED_BACKENDS
- MCP build_feature max_iterations positive validation
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# MCP build_feature backend validation
# ---------------------------------------------------------------------------


class TestBuildFeatureBackendValidation:
    """v182: MCP build_feature rejects unsupported backend names."""

    def _call_build_feature(self, **kwargs):
        """Call build_feature with defaults, overriding with kwargs."""
        defaults = {
            "repo_path": "/tmp/repo",
            "prompt": "add tests",
            "backend": "codexcli",
        }
        defaults.update(kwargs)
        from helping_hands.server.mcp_server import build_feature

        return build_feature(**defaults)

    def test_rejects_empty_backend(self) -> None:
        with pytest.raises(ValueError, match="unsupported backend"):
            self._call_build_feature(backend="")

    def test_rejects_unknown_backend(self) -> None:
        with pytest.raises(ValueError, match="unsupported backend"):
            self._call_build_feature(backend="nonexistent-backend")

    def test_rejects_whitespace_backend(self) -> None:
        with pytest.raises(ValueError, match="unsupported backend"):
            self._call_build_feature(backend="   ")

    def test_error_message_includes_choices(self) -> None:
        with pytest.raises(ValueError, match="expected one of:"):
            self._call_build_feature(backend="bad")

    def test_error_message_includes_backend_name(self) -> None:
        with pytest.raises(ValueError, match="'bad-name'"):
            self._call_build_feature(backend="bad-name")

    def test_accepts_valid_codexcli(self) -> None:
        mock_mod = MagicMock()
        fake_task = MagicMock()
        fake_task.id = "task-1"
        mock_mod.build_feature.delay.return_value = fake_task
        mock_mod._SUPPORTED_BACKENDS = {
            "e2e",
            "basic-langgraph",
            "basic-atomic",
            "basic-agent",
            "codexcli",
            "claudecodecli",
            "docker-sandbox-claude",
            "goose",
            "geminicli",
            "opencodecli",
        }

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            from helping_hands.server.mcp_server import build_feature

            result = build_feature("/tmp/repo", "test", backend="codexcli")

        assert result["backend"] == "codexcli"

    def test_accepts_valid_e2e(self) -> None:
        mock_mod = MagicMock()
        fake_task = MagicMock()
        fake_task.id = "task-2"
        mock_mod.build_feature.delay.return_value = fake_task
        mock_mod._SUPPORTED_BACKENDS = {
            "e2e",
            "basic-langgraph",
            "basic-atomic",
            "basic-agent",
            "codexcli",
            "claudecodecli",
            "docker-sandbox-claude",
            "goose",
            "geminicli",
            "opencodecli",
        }

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            from helping_hands.server.mcp_server import build_feature

            result = build_feature("/tmp/repo", "test", backend="e2e")

        assert result["backend"] == "e2e"

    def test_backend_normalized_case_insensitive(self) -> None:
        mock_mod = MagicMock()
        fake_task = MagicMock()
        fake_task.id = "task-3"
        mock_mod.build_feature.delay.return_value = fake_task
        mock_mod._SUPPORTED_BACKENDS = {
            "e2e",
            "basic-langgraph",
            "basic-atomic",
            "basic-agent",
            "codexcli",
            "claudecodecli",
            "docker-sandbox-claude",
            "goose",
            "geminicli",
            "opencodecli",
        }

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            from helping_hands.server.mcp_server import build_feature

            result = build_feature("/tmp/repo", "test", backend="CodexCLI")

        assert result["backend"] == "CodexCLI"

    def test_accepts_all_supported_backends(self) -> None:
        """Every backend in SUPPORTED_BACKENDS should be accepted."""
        from helping_hands.server.constants import SUPPORTED_BACKENDS

        for backend in sorted(SUPPORTED_BACKENDS):
            mock_mod = MagicMock()
            fake_task = MagicMock()
            fake_task.id = f"task-{backend}"
            mock_mod.build_feature.delay.return_value = fake_task
            mock_mod._SUPPORTED_BACKENDS = SUPPORTED_BACKENDS

            with patch.dict(
                "sys.modules",
                {"helping_hands.server.celery_app": mock_mod},
            ):
                from helping_hands.server.mcp_server import build_feature

                result = build_feature("/tmp/repo", "test", backend=backend)

            assert result["backend"] == backend


# ---------------------------------------------------------------------------
# MCP build_feature max_iterations validation
# ---------------------------------------------------------------------------


class TestBuildFeatureMaxIterationsValidation:
    """v182: MCP build_feature rejects non-positive max_iterations."""

    def test_rejects_zero(self) -> None:
        from helping_hands.server.mcp_server import build_feature

        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            build_feature("/tmp/repo", "test", max_iterations=0)

    def test_rejects_negative(self) -> None:
        from helping_hands.server.mcp_server import build_feature

        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            build_feature("/tmp/repo", "test", max_iterations=-5)

    def test_error_includes_value(self) -> None:
        from helping_hands.server.mcp_server import build_feature

        with pytest.raises(ValueError, match="-3"):
            build_feature("/tmp/repo", "test", max_iterations=-3)

    def test_accepts_one(self) -> None:
        mock_mod = MagicMock()
        fake_task = MagicMock()
        fake_task.id = "task-iter-1"
        mock_mod.build_feature.delay.return_value = fake_task
        mock_mod._SUPPORTED_BACKENDS = {
            "e2e",
            "basic-langgraph",
            "basic-atomic",
            "basic-agent",
            "codexcli",
            "claudecodecli",
            "docker-sandbox-claude",
            "goose",
            "geminicli",
            "opencodecli",
        }

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            from helping_hands.server.mcp_server import build_feature

            result = build_feature(
                "/tmp/repo", "test", max_iterations=1, backend="codexcli"
            )

        assert result["task_id"] == "task-iter-1"

    def test_accepts_large_value(self) -> None:
        mock_mod = MagicMock()
        fake_task = MagicMock()
        fake_task.id = "task-iter-big"
        mock_mod.build_feature.delay.return_value = fake_task
        mock_mod._SUPPORTED_BACKENDS = {
            "e2e",
            "basic-langgraph",
            "basic-atomic",
            "basic-agent",
            "codexcli",
            "claudecodecli",
            "docker-sandbox-claude",
            "goose",
            "geminicli",
            "opencodecli",
        }

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            from helping_hands.server.mcp_server import build_feature

            result = build_feature(
                "/tmp/repo", "test", max_iterations=100, backend="codexcli"
            )

        assert result["task_id"] == "task-iter-big"


# ---------------------------------------------------------------------------
# SUPPORTED_BACKENDS constant in server/constants.py
# ---------------------------------------------------------------------------


class TestSupportedBackendsConstant:
    """v182: SUPPORTED_BACKENDS lives in server/constants.py."""

    def test_is_frozenset(self) -> None:
        from helping_hands.server.constants import SUPPORTED_BACKENDS

        assert isinstance(SUPPORTED_BACKENDS, frozenset)

    def test_contains_expected_backends(self) -> None:
        from helping_hands.server.constants import SUPPORTED_BACKENDS

        expected = {
            "e2e",
            "basic-langgraph",
            "basic-atomic",
            "basic-agent",
            "codexcli",
            "claudecodecli",
            "docker-sandbox-claude",
            "goose",
            "geminicli",
            "opencodecli",
        }
        assert expected == SUPPORTED_BACKENDS

    def test_in_constants_all(self) -> None:
        from helping_hands.server.constants import __all__

        assert "SUPPORTED_BACKENDS" in __all__

    def test_not_empty(self) -> None:
        from helping_hands.server.constants import SUPPORTED_BACKENDS

        assert len(SUPPORTED_BACKENDS) > 0
