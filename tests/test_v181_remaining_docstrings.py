"""Enforce Google-style docstrings on the Docker container wrapper and server health checks.

_wrap_container_if_enabled in cli/base.py controls whether a CLI hand runs inside
a Docker sandbox. Its Raises: contract (RuntimeError when Docker is unavailable) is
the boundary between container mode and bare execution, and is easy to accidentally
remove. The three health-check helpers in server/app.py (_check_redis_health,
_check_db_health, _check_workers_health) feed the /health endpoint; without
documented Returns: sections it is unclear what shape of dict/bool each helper is
expected to return, making it easy for a refactor to break the endpoint response
schema silently.
"""

from __future__ import annotations

import inspect

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

# ---------------------------------------------------------------------------
# cli/base.py — _wrap_container_if_enabled
# ---------------------------------------------------------------------------


class TestWrapContainerIfEnabledDocstring:
    """Verify _wrap_container_if_enabled has a Google-style docstring."""

    def test_has_docstring(self) -> None:
        doc = inspect.getdoc(_TwoPhaseCLIHand._wrap_container_if_enabled)
        assert doc and len(doc.strip()) >= 10

    def test_has_args_section(self) -> None:
        doc = inspect.getdoc(_TwoPhaseCLIHand._wrap_container_if_enabled) or ""
        assert "Args:" in doc

    def test_has_returns_section(self) -> None:
        doc = inspect.getdoc(_TwoPhaseCLIHand._wrap_container_if_enabled) or ""
        assert "Returns:" in doc

    def test_has_raises_section(self) -> None:
        doc = inspect.getdoc(_TwoPhaseCLIHand._wrap_container_if_enabled) or ""
        assert "Raises:" in doc

    def test_mentions_docker(self) -> None:
        doc = inspect.getdoc(_TwoPhaseCLIHand._wrap_container_if_enabled) or ""
        assert "docker" in doc.lower()

    def test_mentions_runtime_error(self) -> None:
        doc = inspect.getdoc(_TwoPhaseCLIHand._wrap_container_if_enabled) or ""
        assert "RuntimeError" in doc


# ---------------------------------------------------------------------------
# server/app.py — health-check helpers (skipped without server extras)
# ---------------------------------------------------------------------------

_HEALTH_FUNCTIONS = [
    "_check_redis_health",
    "_check_db_health",
    "_check_workers_health",
]


def _get_app_mod():
    """Import server.app or skip."""
    return pytest.importorskip(
        "helping_hands.server.app",
        reason="server extras not installed",
    )


class TestHealthCheckDocstrings:
    """Verify the 3 health-check helpers have Google-style docstrings."""

    @pytest.mark.parametrize("func_name", _HEALTH_FUNCTIONS)
    def test_function_has_docstring(self, func_name: str) -> None:
        app_mod = _get_app_mod()
        func = getattr(app_mod, func_name)
        doc = inspect.getdoc(func)
        assert doc and len(doc.strip()) >= 10, f"{func_name} is missing a docstring"

    @pytest.mark.parametrize("func_name", _HEALTH_FUNCTIONS)
    def test_function_has_returns_section(self, func_name: str) -> None:
        app_mod = _get_app_mod()
        func = getattr(app_mod, func_name)
        doc = inspect.getdoc(func) or ""
        assert "Returns:" in doc, f"{func_name} is missing Returns section"

    def test_check_redis_mentions_broker(self) -> None:
        app_mod = _get_app_mod()
        doc = inspect.getdoc(app_mod._check_redis_health) or ""
        assert "broker" in doc.lower()

    def test_check_db_mentions_database_url(self) -> None:
        app_mod = _get_app_mod()
        doc = inspect.getdoc(app_mod._check_db_health) or ""
        assert "DATABASE_URL" in doc

    def test_check_db_mentions_na(self) -> None:
        app_mod = _get_app_mod()
        doc = inspect.getdoc(app_mod._check_db_health) or ""
        assert "na" in doc

    def test_check_workers_mentions_ping(self) -> None:
        app_mod = _get_app_mod()
        doc = inspect.getdoc(app_mod._check_workers_health) or ""
        assert "ping" in doc.lower()
