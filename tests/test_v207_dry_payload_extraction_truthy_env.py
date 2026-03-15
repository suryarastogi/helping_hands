"""Tests for v207: DRY payload extraction helper, truthy env var consistency.

Verifies:
- _is_truthy_env now strips whitespace
- pr_description._is_disabled delegates to _is_truthy_env
- e2e._draft_pr_enabled delegates to _is_truthy_env
- _extract_str_field shared helper works correctly
- _extract_task_id and _extract_task_name delegate to _extract_str_field
- _TASK_ID_KEYS and _TASK_NAME_KEYS are correct tuples
- app._is_running_in_docker uses _is_truthy_env
"""

from __future__ import annotations

import importlib

import pytest

from helping_hands.lib.config import _is_truthy_env
from helping_hands.lib.hands.v1.hand.e2e import E2EHand
from helping_hands.lib.hands.v1.hand.pr_description import (
    _DISABLE_ENV_VAR,
    _is_disabled,
)

_has_fastapi = importlib.util.find_spec("fastapi") is not None

# ---------------------------------------------------------------------------
# 1. _is_truthy_env whitespace stripping
# ---------------------------------------------------------------------------


class TestIsTruthyEnvStrip:
    """Verify _is_truthy_env strips whitespace from env var values."""

    def test_strips_leading_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_TRUTHY_STRIP", "  true")
        assert _is_truthy_env("TEST_TRUTHY_STRIP") is True

    def test_strips_trailing_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_TRUTHY_STRIP", "yes  ")
        assert _is_truthy_env("TEST_TRUTHY_STRIP") is True

    def test_strips_surrounding_whitespace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_TRUTHY_STRIP", "  1  ")
        assert _is_truthy_env("TEST_TRUTHY_STRIP") is True

    def test_non_truthy_after_strip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_TRUTHY_STRIP", "  nope  ")
        assert _is_truthy_env("TEST_TRUTHY_STRIP") is False

    def test_default_with_whitespace(self) -> None:
        assert _is_truthy_env("TEST_TRUTHY_NONEXISTENT_VAR_207") is False


# ---------------------------------------------------------------------------
# 2. pr_description._is_disabled uses _is_truthy_env
# ---------------------------------------------------------------------------


class TestPrDescriptionIsDisabled:
    """Verify _is_disabled delegates to _is_truthy_env."""

    def test_disabled_when_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_DISABLE_ENV_VAR, "true")
        assert _is_disabled() is True

    def test_disabled_when_yes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_DISABLE_ENV_VAR, "yes")
        assert _is_disabled() is True

    def test_disabled_when_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_DISABLE_ENV_VAR, "1")
        assert _is_disabled() is True

    def test_not_disabled_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(_DISABLE_ENV_VAR, raising=False)
        assert _is_disabled() is False

    def test_not_disabled_when_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_DISABLE_ENV_VAR, "false")
        assert _is_disabled() is False

    def test_on_no_longer_truthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """'on' was previously accepted but is now aligned with _TRUTHY_VALUES."""
        monkeypatch.setenv(_DISABLE_ENV_VAR, "on")
        assert _is_disabled() is False

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_DISABLE_ENV_VAR, "  true  ")
        assert _is_disabled() is True


# ---------------------------------------------------------------------------
# 3. e2e._draft_pr_enabled uses _is_truthy_env
# ---------------------------------------------------------------------------


class TestE2EDraftPrEnabled:
    """Verify _draft_pr_enabled delegates to _is_truthy_env."""

    def test_enabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_E2E_DRAFT_PR", raising=False)
        assert E2EHand._draft_pr_enabled() is True

    def test_disabled_when_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "false")
        assert E2EHand._draft_pr_enabled() is False

    def test_enabled_when_yes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "yes")
        assert E2EHand._draft_pr_enabled() is True

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "  true  ")
        assert E2EHand._draft_pr_enabled() is True


# ---------------------------------------------------------------------------
# 4. _extract_str_field shared helper (requires fastapi)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_fastapi, reason="server extras not installed")
class TestExtractStrField:
    """Verify the shared _extract_str_field helper."""

    def test_returns_first_matching_key(self) -> None:
        from helping_hands.server.app import _extract_str_field

        entry = {"a": "alpha", "b": "beta"}
        assert _extract_str_field(entry, ("a", "b")) == "alpha"

    def test_skips_non_string_values(self) -> None:
        from helping_hands.server.app import _extract_str_field

        entry = {"a": 123, "b": "beta"}
        assert _extract_str_field(entry, ("a", "b")) == "beta"

    def test_skips_empty_string_values(self) -> None:
        from helping_hands.server.app import _extract_str_field

        entry = {"a": "", "b": "beta"}
        assert _extract_str_field(entry, ("a", "b")) == "beta"

    def test_skips_whitespace_only_values(self) -> None:
        from helping_hands.server.app import _extract_str_field

        entry = {"a": "   ", "b": "beta"}
        assert _extract_str_field(entry, ("a", "b")) == "beta"

    def test_strips_whitespace_from_result(self) -> None:
        from helping_hands.server.app import _extract_str_field

        entry = {"a": "  alpha  "}
        assert _extract_str_field(entry, ("a",)) == "alpha"

    def test_recurses_into_request(self) -> None:
        from helping_hands.server.app import _extract_str_field

        entry = {"request": {"a": "nested"}}
        assert _extract_str_field(entry, ("a",)) == "nested"

    def test_returns_none_when_missing(self) -> None:
        from helping_hands.server.app import _extract_str_field

        assert _extract_str_field({}, ("x", "y")) is None

    def test_returns_none_when_no_matching_keys(self) -> None:
        from helping_hands.server.app import _extract_str_field

        entry = {"unrelated": "value"}
        assert _extract_str_field(entry, ("a", "b")) is None

    def test_returns_none_for_nested_empty(self) -> None:
        from helping_hands.server.app import _extract_str_field

        entry = {"request": {"a": "  "}}
        assert _extract_str_field(entry, ("a",)) is None

    def test_ignores_non_dict_request(self) -> None:
        from helping_hands.server.app import _extract_str_field

        entry = {"request": "not-a-dict"}
        assert _extract_str_field(entry, ("a",)) is None

    def test_prefers_direct_over_nested(self) -> None:
        from helping_hands.server.app import _extract_str_field

        entry = {"a": "direct", "request": {"a": "nested"}}
        assert _extract_str_field(entry, ("a",)) == "direct"


@pytest.mark.skipif(not _has_fastapi, reason="server extras not installed")
class TestTaskKeyConstants:
    """Verify key constant tuples are correct."""

    def test_task_id_keys(self) -> None:
        from helping_hands.server.app import _TASK_ID_KEYS

        assert _TASK_ID_KEYS == ("task_id", "uuid", "id")

    def test_task_name_keys(self) -> None:
        from helping_hands.server.app import _TASK_NAME_KEYS

        assert _TASK_NAME_KEYS == ("name", "task")


@pytest.mark.skipif(not _has_fastapi, reason="server extras not installed")
class TestExtractDelegation:
    """Verify _extract_task_id and _extract_task_name delegate."""

    def test_extract_task_id_uses_id_keys(self) -> None:
        from helping_hands.server.app import _TASK_ID_KEYS, _extract_task_id

        for key in _TASK_ID_KEYS:
            assert _extract_task_id({key: "val"}) == "val"

    def test_extract_task_name_uses_name_keys(self) -> None:
        from helping_hands.server.app import _TASK_NAME_KEYS, _extract_task_name

        for key in _TASK_NAME_KEYS:
            assert _extract_task_name({key: "val"}) == "val"

    def test_extract_task_id_nested(self) -> None:
        from helping_hands.server.app import _extract_task_id

        assert _extract_task_id({"request": {"uuid": "nested"}}) == "nested"

    def test_extract_task_name_nested(self) -> None:
        from helping_hands.server.app import _extract_task_name

        assert _extract_task_name({"request": {"name": "nested"}}) == "nested"


# ---------------------------------------------------------------------------
# 5. app._is_running_in_docker uses _is_truthy_env (requires fastapi)
# ---------------------------------------------------------------------------


class _FakePathNoDockerenv:
    """Fake Path that always returns False for .exists() on /.dockerenv."""

    def __init__(self, path: str) -> None:
        self._path = path

    def exists(self) -> bool:
        return False


@pytest.mark.skipif(not _has_fastapi, reason="server extras not installed")
class TestIsRunningInDockerTruthy:
    """Verify _is_running_in_docker delegates truthy check to _is_truthy_env."""

    def test_truthy_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _is_running_in_docker

        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "1")
        monkeypatch.setattr("helping_hands.server.app.Path", _FakePathNoDockerenv)
        assert _is_running_in_docker() is True

    def test_falsy_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _is_running_in_docker

        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "no")
        monkeypatch.setattr("helping_hands.server.app.Path", _FakePathNoDockerenv)
        assert _is_running_in_docker() is False

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _is_running_in_docker

        monkeypatch.setenv("HELPING_HANDS_IN_DOCKER", "  yes  ")
        monkeypatch.setattr("helping_hands.server.app.Path", _FakePathNoDockerenv)
        assert _is_running_in_docker() is True

    def test_unset_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.server.app import _is_running_in_docker

        monkeypatch.delenv("HELPING_HANDS_IN_DOCKER", raising=False)
        monkeypatch.setattr("helping_hands.server.app.Path", _FakePathNoDockerenv)
        assert _is_running_in_docker() is False
