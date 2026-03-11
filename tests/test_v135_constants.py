"""Tests for v135: extracted magic number constants in mcp_server and celery_app."""

from __future__ import annotations

import inspect

import pytest


class TestMcpServerConstants:
    """Tests for _DEFAULT_EXEC_TIMEOUT_S and _DEFAULT_BROWSE_MAX_CHARS."""

    def test_default_exec_timeout_value(self) -> None:
        from helping_hands.server.mcp_server import _DEFAULT_EXEC_TIMEOUT_S

        assert _DEFAULT_EXEC_TIMEOUT_S == 60

    def test_default_browse_max_chars_value(self) -> None:
        from helping_hands.server.mcp_server import _DEFAULT_BROWSE_MAX_CHARS

        assert _DEFAULT_BROWSE_MAX_CHARS == 12000

    def test_run_python_code_uses_timeout_constant(self) -> None:
        from helping_hands.server.mcp_server import (
            _DEFAULT_EXEC_TIMEOUT_S,
            run_python_code,
        )

        sig = inspect.signature(run_python_code)
        assert sig.parameters["timeout_s"].default == _DEFAULT_EXEC_TIMEOUT_S

    def test_run_python_script_uses_timeout_constant(self) -> None:
        from helping_hands.server.mcp_server import (
            _DEFAULT_EXEC_TIMEOUT_S,
            run_python_script,
        )

        sig = inspect.signature(run_python_script)
        assert sig.parameters["timeout_s"].default == _DEFAULT_EXEC_TIMEOUT_S

    def test_run_bash_script_uses_timeout_constant(self) -> None:
        from helping_hands.server.mcp_server import (
            _DEFAULT_EXEC_TIMEOUT_S,
            run_bash_script,
        )

        sig = inspect.signature(run_bash_script)
        assert sig.parameters["timeout_s"].default == _DEFAULT_EXEC_TIMEOUT_S

    def test_web_browse_uses_max_chars_constant(self) -> None:
        from helping_hands.server.mcp_server import (
            _DEFAULT_BROWSE_MAX_CHARS,
            web_browse,
        )

        sig = inspect.signature(web_browse)
        assert sig.parameters["max_chars"].default == _DEFAULT_BROWSE_MAX_CHARS

    def test_constants_are_positive_integers(self) -> None:
        from helping_hands.server.mcp_server import (
            _DEFAULT_BROWSE_MAX_CHARS,
            _DEFAULT_EXEC_TIMEOUT_S,
        )

        assert isinstance(_DEFAULT_EXEC_TIMEOUT_S, int)
        assert _DEFAULT_EXEC_TIMEOUT_S > 0
        assert isinstance(_DEFAULT_BROWSE_MAX_CHARS, int)
        assert _DEFAULT_BROWSE_MAX_CHARS > 0


class TestCeleryAppUsageLogInterval:
    """Tests for _USAGE_LOG_INTERVAL_S constant."""

    def test_usage_log_interval_value(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _USAGE_LOG_INTERVAL_S

        assert _USAGE_LOG_INTERVAL_S == 3600.0

    def test_usage_log_interval_is_positive_float(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _USAGE_LOG_INTERVAL_S

        assert isinstance(_USAGE_LOG_INTERVAL_S, float)
        assert _USAGE_LOG_INTERVAL_S > 0

    def test_usage_log_interval_is_one_hour(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _USAGE_LOG_INTERVAL_S

        assert _USAGE_LOG_INTERVAL_S == 60.0 * 60.0  # 1 hour in seconds
