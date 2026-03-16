"""Tests for v234 — DEFAULT_REDIS_URL constant, health check & DB exception narrowing.

Covers:
- ``server/constants`` new ``DEFAULT_REDIS_URL`` constant
- ``celery_app`` uses ``_DEFAULT_REDIS_URL`` instead of bare string
- ``app`` uses ``_DEFAULT_REDIS_URL`` instead of bare string
- Health check exception handlers narrowed (no bare ``except Exception``)
- ``log_claude_usage`` DB write handler narrowed
- ``ensure_usage_schedule`` handler narrowed
- Runtime tests for ``ImportError`` paths in health checks and DB write
"""

from __future__ import annotations

import ast
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _server_available() -> bool:
    """Check if server extras (fastapi etc.) are installed."""
    try:
        import fastapi  # noqa: F401

        return True
    except ImportError:
        return False


def _src_root() -> Path:
    """Return the path to src/helping_hands/server/."""
    return Path(__file__).resolve().parent.parent / "src" / "helping_hands" / "server"


# ---------------------------------------------------------------------------
# server/constants — DEFAULT_REDIS_URL
# ---------------------------------------------------------------------------


class TestDefaultRedisUrlConstant:
    """Verify DEFAULT_REDIS_URL in server/constants."""

    def test_value(self) -> None:
        from helping_hands.server.constants import DEFAULT_REDIS_URL

        assert DEFAULT_REDIS_URL == "redis://localhost:6379/0"

    def test_is_string(self) -> None:
        from helping_hands.server.constants import DEFAULT_REDIS_URL

        assert isinstance(DEFAULT_REDIS_URL, str)

    def test_in_all(self) -> None:
        from helping_hands.server import constants

        assert "DEFAULT_REDIS_URL" in constants.__all__

    def test_all_symbols_importable(self) -> None:
        from helping_hands.server import constants

        for name in constants.__all__:
            assert hasattr(constants, name), (
                f"{name} declared in __all__ but not importable"
            )


# ---------------------------------------------------------------------------
# Source consistency — no bare "redis://localhost:6379/0" in celery_app/app
# ---------------------------------------------------------------------------


class TestNoHardcodedRedisUrl:
    """Verify bare Redis URL strings replaced by constant reference."""

    def test_celery_app_no_bare_redis_url(self) -> None:
        source = (_src_root() / "celery_app.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and node.value == "redis://localhost:6379/0"
            ):
                pytest.fail(
                    "celery_app.py still contains bare 'redis://localhost:6379/0' literal"
                )

    def test_app_no_bare_redis_url(self) -> None:
        source = (_src_root() / "app.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and node.value == "redis://localhost:6379/0"
            ):
                pytest.fail(
                    "app.py still contains bare 'redis://localhost:6379/0' literal"
                )

    def test_celery_app_imports_default_redis_url(self) -> None:
        source = (_src_root() / "celery_app.py").read_text()
        assert "_DEFAULT_REDIS_URL" in source

    def test_app_imports_default_redis_url(self) -> None:
        source = (_src_root() / "app.py").read_text()
        assert "_DEFAULT_REDIS_URL" in source


# ---------------------------------------------------------------------------
# AST — health check exception narrowing
# ---------------------------------------------------------------------------


def _get_except_handler_types(source: str, func_name: str) -> list[list[str]]:
    """Return exception type names for each handler in a function."""
    tree = ast.parse(source)
    handlers: list[list[str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            for child in ast.walk(node):
                if isinstance(child, ast.ExceptHandler) and child.type:
                    if isinstance(child.type, ast.Tuple):
                        names = []
                        for elt in child.type.elts:
                            if isinstance(elt, ast.Name):
                                names.append(elt.id)
                            elif isinstance(elt, ast.Attribute):
                                names.append(elt.attr)
                        handlers.append(names)
                    elif isinstance(child.type, ast.Name):
                        handlers.append([child.type.id])
                    elif isinstance(child.type, ast.Attribute):
                        handlers.append([child.type.attr])
    return handlers


class TestHealthCheckExceptionNarrowing:
    """Verify health check handlers don't use bare except Exception."""

    def test_check_redis_health_no_bare_exception(self) -> None:
        source = (_src_root() / "app.py").read_text()
        handlers = _get_except_handler_types(source, "_check_redis_health")
        flat = [name for group in handlers for name in group]
        assert "Exception" not in flat, (
            "_check_redis_health should not have bare 'except Exception'"
        )

    def test_check_redis_health_catches_import_error(self) -> None:
        source = (_src_root() / "app.py").read_text()
        handlers = _get_except_handler_types(source, "_check_redis_health")
        flat = [name for group in handlers for name in group]
        assert "ImportError" in flat

    def test_check_redis_health_catches_redis_error(self) -> None:
        source = (_src_root() / "app.py").read_text()
        handlers = _get_except_handler_types(source, "_check_redis_health")
        flat = [name for group in handlers for name in group]
        assert "RedisError" in flat

    def test_check_redis_health_catches_os_error(self) -> None:
        source = (_src_root() / "app.py").read_text()
        handlers = _get_except_handler_types(source, "_check_redis_health")
        flat = [name for group in handlers for name in group]
        assert "OSError" in flat

    def test_check_db_health_no_bare_exception(self) -> None:
        source = (_src_root() / "app.py").read_text()
        handlers = _get_except_handler_types(source, "_check_db_health")
        flat = [name for group in handlers for name in group]
        assert "Exception" not in flat, (
            "_check_db_health should not have bare 'except Exception'"
        )

    def test_check_db_health_catches_import_error(self) -> None:
        source = (_src_root() / "app.py").read_text()
        handlers = _get_except_handler_types(source, "_check_db_health")
        flat = [name for group in handlers for name in group]
        assert "ImportError" in flat

    def test_check_db_health_catches_psycopg2_error(self) -> None:
        source = (_src_root() / "app.py").read_text()
        handlers = _get_except_handler_types(source, "_check_db_health")
        flat = [name for group in handlers for name in group]
        assert "Error" in flat

    def test_check_db_health_catches_os_error(self) -> None:
        source = (_src_root() / "app.py").read_text()
        handlers = _get_except_handler_types(source, "_check_db_health")
        flat = [name for group in handlers for name in group]
        assert "OSError" in flat


# ---------------------------------------------------------------------------
# AST — celery_app exception narrowing
# ---------------------------------------------------------------------------


class TestCeleryExceptionNarrowing:
    """Verify celery_app handlers narrowed."""

    def test_log_claude_usage_no_bare_exception(self) -> None:
        """log_claude_usage should have zero bare 'except Exception' handlers."""
        source = (_src_root() / "celery_app.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "log_claude_usage":
                bare = sum(
                    1
                    for child in ast.walk(node)
                    if isinstance(child, ast.ExceptHandler)
                    and isinstance(child.type, ast.Name)
                    and child.type.id == "Exception"
                )
                assert bare == 0, (
                    f"log_claude_usage has {bare} bare 'except Exception' handlers"
                )

    def test_log_claude_usage_db_catches_import_error(self) -> None:
        source = (_src_root() / "celery_app.py").read_text()
        handlers = _get_except_handler_types(source, "log_claude_usage")
        flat = [name for group in handlers for name in group]
        assert "ImportError" in flat

    def test_log_claude_usage_db_catches_psycopg2_error(self) -> None:
        source = (_src_root() / "celery_app.py").read_text()
        handlers = _get_except_handler_types(source, "log_claude_usage")
        flat = [name for group in handlers for name in group]
        # psycopg2.Error appears as "Error" in AST attribute form
        assert "Error" in flat

    def test_ensure_usage_schedule_no_bare_exception(self) -> None:
        """ensure_usage_schedule should not have bare 'except Exception'."""
        source = (_src_root() / "celery_app.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "ensure_usage_schedule"
            ):
                bare = sum(
                    1
                    for child in ast.walk(node)
                    if isinstance(child, ast.ExceptHandler)
                    and isinstance(child.type, ast.Name)
                    and child.type.id == "Exception"
                )
                assert bare == 0, (
                    f"ensure_usage_schedule has {bare} bare 'except Exception'"
                )

    def test_ensure_usage_schedule_catches_import_error(self) -> None:
        source = (_src_root() / "celery_app.py").read_text()
        handlers = _get_except_handler_types(source, "ensure_usage_schedule")
        flat = [name for group in handlers for name in group]
        assert "ImportError" in flat

    def test_ensure_usage_schedule_catches_os_error(self) -> None:
        source = (_src_root() / "celery_app.py").read_text()
        handlers = _get_except_handler_types(source, "ensure_usage_schedule")
        flat = [name for group in handlers for name in group]
        assert "OSError" in flat


# ---------------------------------------------------------------------------
# Runtime — ImportError paths in health checks
# ---------------------------------------------------------------------------

_skip_no_server = pytest.mark.skipif(
    not _server_available(),
    reason="server extras not installed",
)


@_skip_no_server
class TestHealthCheckImportErrorPaths:
    """Verify health checks return 'error' when packages are missing."""

    def test_redis_import_error_returns_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.server.app import _check_redis_health

        monkeypatch.setitem(sys.modules, "redis", None)

        assert _check_redis_health() == "error"

    def test_redis_redis_error_returns_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.server.app import _check_redis_health

        fake_redis_error = type("RedisError", (Exception,), {})
        mock_redis_cls = MagicMock()
        mock_redis_cls.from_url.side_effect = fake_redis_error("connection lost")

        fake_redis = types.ModuleType("redis")
        fake_redis.Redis = mock_redis_cls  # type: ignore[attr-defined]
        fake_redis.RedisError = fake_redis_error  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "redis", fake_redis)

        assert _check_redis_health() == "error"

    def test_db_import_error_returns_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.server.app import _check_db_health

        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setitem(sys.modules, "psycopg2", None)

        assert _check_db_health() == "error"

    def test_db_psycopg2_error_returns_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.server.app import _check_db_health

        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

        fake_pg_error = type("Error", (Exception,), {})
        mock_psycopg2 = MagicMock()
        mock_psycopg2.Error = fake_pg_error
        mock_psycopg2.connect.side_effect = fake_pg_error("auth failed")
        monkeypatch.setitem(sys.modules, "psycopg2", mock_psycopg2)

        assert _check_db_health() == "error"


# ---------------------------------------------------------------------------
# Runtime — ImportError path in log_claude_usage DB write
# ---------------------------------------------------------------------------


@_skip_no_server
class TestLogClaudeUsageDbImportError:
    """Verify log_claude_usage returns error when psycopg2 is missing."""

    @staticmethod
    def _make_keychain_result(
        token: str = "ey-test",
    ) -> Any:
        import subprocess

        payload = f'{{"claudeAiOauth": {{"accessToken": "{token}"}}}}'
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=payload)

    def test_psycopg2_import_error_returns_db_failed(self) -> None:
        import json
        import os

        from helping_hands.server import celery_app

        usage_data = json.dumps(
            {
                "five_hour": {"utilization": 0.4, "resets_at": "2026-03-06T12:00:00Z"},
                "seven_day": {"utilization": 0.2, "resets_at": "2026-03-10T00:00:00Z"},
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = usage_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with (
            patch(
                "helping_hands.server.celery_app.subprocess.run",
                return_value=self._make_keychain_result(),
            ),
            patch("urllib.request.urlopen", return_value=mock_resp),
            patch.dict("sys.modules", {"psycopg2": None}),
            patch.dict(
                os.environ, {"DATABASE_URL": "postgres://test:test@localhost/test"}
            ),
        ):
            result = celery_app.log_claude_usage()

        assert result["status"] == "error"
        assert "DB write failed" in result["message"]
        assert result["session_pct"] == 0.4
        assert result["weekly_pct"] == 0.2
