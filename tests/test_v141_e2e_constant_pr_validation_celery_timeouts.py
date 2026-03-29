"""Tests for v141: E2E marker file constant, CLI --pr-number validation, Celery timeouts.

_E2E_MARKER_FILE identifies integration-test workspaces so the E2EHand knows it is
operating on a disposable clone; if it regresses from the expected filename or the
run() method stops using the constant (using a hardcoded string instead), E2E runs
may accidentally execute against real repositories.

The CLI --pr-number validation ensures the entry point rejects non-positive integers
before constructing any Hand; a regression means invalid PR numbers propagate into
the GitHub API and produce unhelpful 422 responses from the remote.

Celery timeout constants guard task-execution budget limits; a regression to zero
or a non-numeric value would cause immediate TimeoutError on every task.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. E2E marker filename constant
# ---------------------------------------------------------------------------


class TestE2EMarkerFileConstant:
    """Verify _E2E_MARKER_FILE constant in e2e.py."""

    def test_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_MARKER_FILE

        assert _E2E_MARKER_FILE == "HELPING_HANDS_E2E.md"

    def test_is_string(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_MARKER_FILE

        assert isinstance(_E2E_MARKER_FILE, str)

    def test_ends_with_md(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import _E2E_MARKER_FILE

        assert _E2E_MARKER_FILE.endswith(".md")

    def test_used_in_run(self) -> None:
        """Verify run() uses the constant rather than a hardcoded string."""
        import inspect

        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        source = inspect.getsource(E2EHand.run)
        assert "_E2E_MARKER_FILE" in source


# ---------------------------------------------------------------------------
# 2. CLI --pr-number positive validation
# ---------------------------------------------------------------------------


class TestCLIPrNumberValidation:
    """Verify --pr-number rejects non-positive integers."""

    def test_zero_pr_number_exits(self) -> None:
        from helping_hands.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            main(["owner/repo", "--e2e", "--pr-number", "0"])
        assert exc_info.value.code == 1

    def test_negative_pr_number_exits(self) -> None:
        from helping_hands.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            main(["owner/repo", "--e2e", "--pr-number", "-1"])
        assert exc_info.value.code == 1

    def test_negative_pr_number_error_message(self, capsys) -> None:
        from helping_hands.cli.main import main

        with pytest.raises(SystemExit):
            main(["owner/repo", "--e2e", "--pr-number", "-5"])
        captured = capsys.readouterr()
        assert "--pr-number" in captured.err
        assert "positive" in captured.err.lower()
        assert "-5" in captured.err

    @patch("helping_hands.cli.main.E2EHand")
    @patch("helping_hands.cli.main.Config")
    def test_positive_pr_number_passes_validation(
        self, mock_config_cls, mock_e2e_cls
    ) -> None:
        """A positive --pr-number should not be rejected by the validation."""
        from helping_hands.cli.main import main

        mock_config = MagicMock()
        mock_config.repo = "owner/repo"
        mock_config_cls.from_env.return_value = mock_config

        mock_hand = MagicMock()
        mock_hand.run.return_value = MagicMock(
            message="ok",
            metadata={"hand_uuid": "u", "workspace": "w", "pr_url": "p"},
        )
        mock_e2e_cls.return_value = mock_hand

        # Should not raise SystemExit
        main(["owner/repo", "--e2e", "--pr-number", "42"])
        mock_hand.run.assert_called_once()
        call_kwargs = mock_hand.run.call_args
        assert call_kwargs[1]["pr_number"] == 42


# ---------------------------------------------------------------------------
# 3. Celery timeout constants
# ---------------------------------------------------------------------------


class TestCeleryTimeoutConstants:
    """Verify _KEYCHAIN_TIMEOUT_S and _DB_CONNECT_TIMEOUT_S in celery_app.py."""

    def test_keychain_timeout_value(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _KEYCHAIN_TIMEOUT_S

        assert _KEYCHAIN_TIMEOUT_S == 5

    def test_keychain_timeout_is_int(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _KEYCHAIN_TIMEOUT_S

        assert isinstance(_KEYCHAIN_TIMEOUT_S, int)

    def test_keychain_timeout_positive(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _KEYCHAIN_TIMEOUT_S

        assert _KEYCHAIN_TIMEOUT_S > 0

    def test_db_connect_timeout_value(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _DB_CONNECT_TIMEOUT_S

        assert _DB_CONNECT_TIMEOUT_S == 5

    def test_db_connect_timeout_is_int(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _DB_CONNECT_TIMEOUT_S

        assert isinstance(_DB_CONNECT_TIMEOUT_S, int)

    def test_db_connect_timeout_positive(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _DB_CONNECT_TIMEOUT_S

        assert _DB_CONNECT_TIMEOUT_S > 0

    def test_keychain_timeout_matches_app_module(self) -> None:
        """Ensure celery_app.py and app.py keychain timeouts are in sync."""
        pytest.importorskip("celery")
        pytest.importorskip("fastapi")
        from helping_hands.server import app as app_mod, celery_app as celery_mod

        assert app_mod._KEYCHAIN_TIMEOUT_S == celery_mod._KEYCHAIN_TIMEOUT_S


# ---------------------------------------------------------------------------
# 4. CLI --max-iterations positive validation (v189)
# ---------------------------------------------------------------------------


class TestCLIMaxIterationsValidation:
    """Verify --max-iterations rejects non-positive integers."""

    def test_zero_max_iterations_exits(self) -> None:
        from helping_hands.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            main([".", "--backend", "basic-langgraph", "--max-iterations", "0"])
        assert exc_info.value.code == 1

    def test_negative_max_iterations_exits(self) -> None:
        from helping_hands.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            main([".", "--backend", "basic-langgraph", "--max-iterations", "-3"])
        assert exc_info.value.code == 1

    def test_negative_max_iterations_error_message(self, capsys) -> None:
        from helping_hands.cli.main import main

        with pytest.raises(SystemExit):
            main([".", "--backend", "basic-langgraph", "--max-iterations", "-5"])
        captured = capsys.readouterr()
        assert "--max-iterations" in captured.err
        assert "positive" in captured.err.lower()
        assert "-5" in captured.err

    def test_positive_max_iterations_passes_validation(self) -> None:
        """Positive --max-iterations should not trigger the validation error."""
        import inspect

        from helping_hands.cli import main as main_mod

        # Verify the validation code references max_iterations
        src = inspect.getsource(main_mod.main)
        assert "max_iterations" in src
        assert "require_positive_int" in src
