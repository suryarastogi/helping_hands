"""Tests for schedules.py coverage gaps: _check_optional_dep and get_schedule_manager.

Covers the two remaining untested functions in schedules.py.
``_check_optional_dep`` is the shared dependency-check helper used by
``_check_redbeat`` and ``_check_croniter``; ``get_schedule_manager`` is the
trivial factory function.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("celery")

from helping_hands.server.schedules import (
    ScheduleManager,
    _check_optional_dep,
    get_schedule_manager,
)


class TestCheckOptionalDep:
    def test_passes_when_available_true(self) -> None:
        _check_optional_dep(True, "some-package", "extra")

    def test_passes_when_available_is_module(self) -> None:
        import json

        _check_optional_dep(json, "json module", "stdlib")

    def test_raises_when_available_false(self) -> None:
        with pytest.raises(ImportError, match="some-package"):
            _check_optional_dep(False, "some-package", "server")

    def test_raises_when_available_none(self) -> None:
        with pytest.raises(ImportError, match="missing-dep"):
            _check_optional_dep(None, "missing-dep", "extra")

    def test_error_message_includes_install_hint(self) -> None:
        with pytest.raises(ImportError, match="uv sync"):
            _check_optional_dep(False, "celery-redbeat", "server")


class TestGetScheduleManager:
    def test_returns_schedule_manager_instance(self) -> None:
        mock_app = MagicMock()
        mock_app.conf.get.return_value = "redis://localhost:6379/0"
        mock_app.conf.broker_url = "redis://localhost:6379/0"
        with patch.dict("sys.modules", {"redis": MagicMock()}):
            result = get_schedule_manager(mock_app)
        assert isinstance(result, ScheduleManager)
        assert result._app is mock_app
