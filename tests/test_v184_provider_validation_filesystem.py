"""Tests for v184: AI provider empty message validation, mkdir_path hardening,
normalize_messages content type check."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from helping_hands.lib.ai_providers.types import AIProvider, normalize_messages

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeProvider(AIProvider):
    name = "fake"
    api_key_env_var = "FAKE_API_KEY"
    default_model = "fake-model"
    install_hint = "none"

    def _build_inner(self) -> Any:
        return {"client": "fake"}

    def _complete_impl(
        self,
        *,
        inner: Any,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> Any:
        return {
            "inner": inner,
            "messages": messages,
            "model": model,
            "kwargs": kwargs,
        }


# ---------------------------------------------------------------------------
# AIProvider.complete() — empty message validation (lifted from Google)
# ---------------------------------------------------------------------------


class TestCompleteEmptyMessageValidation:
    """Base class complete() rejects messages where all content is empty."""

    def test_all_empty_content_raises_value_error(self) -> None:
        provider = _FakeProvider(inner={"x": 1})
        with pytest.raises(ValueError, match="all messages have empty content"):
            provider.complete(
                [
                    {"role": "user", "content": ""},
                    {"role": "assistant", "content": ""},
                ]
            )

    def test_single_empty_message_raises_value_error(self) -> None:
        provider = _FakeProvider(inner={"x": 1})
        with pytest.raises(ValueError, match="all messages have empty content"):
            provider.complete([{"role": "user", "content": ""}])

    def test_missing_content_key_raises_value_error(self) -> None:
        provider = _FakeProvider(inner={"x": 1})
        with pytest.raises(ValueError, match="all messages have empty content"):
            provider.complete([{"role": "user"}])

    def test_mixed_empty_and_valid_passes(self) -> None:
        provider = _FakeProvider(inner={"x": 1})
        result = provider.complete(
            [
                {"role": "system", "content": ""},
                {"role": "user", "content": "hello"},
            ]
        )
        assert result["messages"][1]["content"] == "hello"

    def test_valid_content_passes(self) -> None:
        provider = _FakeProvider(inner={"x": 1})
        result = provider.complete("hello")
        assert result["messages"][0]["content"] == "hello"

    def test_empty_sequence_raises_value_error(self) -> None:
        """An empty message list has no content at all."""
        provider = _FakeProvider(inner={"x": 1})
        with pytest.raises(ValueError, match="all messages have empty content"):
            provider.complete([])


# ---------------------------------------------------------------------------
# normalize_messages — content type validation
# ---------------------------------------------------------------------------


class TestNormalizeMessagesContentTypeValidation:
    """normalize_messages() rejects non-string content values."""

    def test_int_content_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match=r"index 0.*got int"):
            normalize_messages([{"role": "user", "content": 42}])

    def test_list_content_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match=r"index 0.*got list"):
            normalize_messages([{"role": "user", "content": ["a", "b"]}])

    def test_dict_content_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match=r"index 0.*got dict"):
            normalize_messages([{"role": "user", "content": {"key": "val"}}])

    def test_bool_content_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match=r"index 0.*got bool"):
            normalize_messages([{"role": "user", "content": True}])

    def test_float_content_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match=r"index 1.*got float"):
            normalize_messages(
                [
                    {"role": "user", "content": "ok"},
                    {"role": "assistant", "content": 3.14},
                ]
            )

    def test_none_content_accepted(self) -> None:
        """None is a valid content value (normalizes to empty string)."""
        result = normalize_messages([{"role": "user", "content": None}])
        assert result == [{"role": "user", "content": ""}]

    def test_string_content_accepted(self) -> None:
        result = normalize_messages([{"role": "user", "content": "hello"}])
        assert result == [{"role": "user", "content": "hello"}]


# ---------------------------------------------------------------------------
# mkdir_path — OSError handling
# ---------------------------------------------------------------------------


class TestMkdirPathOSError:
    """mkdir_path() wraps OSError in RuntimeError with context."""

    def test_permission_error_raises_runtime_error(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.filesystem import mkdir_path

        with (
            patch("pathlib.Path.mkdir", side_effect=PermissionError("denied")),
            pytest.raises(RuntimeError, match="cannot create directory"),
        ):
            mkdir_path(tmp_path, "subdir")

    def test_oserror_includes_path_context(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.filesystem import mkdir_path

        with (
            patch("pathlib.Path.mkdir", side_effect=OSError("disk full")),
            pytest.raises(RuntimeError, match=r"subdir.*disk full"),
        ):
            mkdir_path(tmp_path, "subdir")

    def test_oserror_wraps_original(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.filesystem import mkdir_path

        original = OSError("original error")
        with patch("pathlib.Path.mkdir", side_effect=original):
            with pytest.raises(RuntimeError) as exc_info:
                mkdir_path(tmp_path, "subdir")
            assert exc_info.value.__cause__ is original

    def test_success_returns_normalized_path(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.filesystem import mkdir_path

        result = mkdir_path(tmp_path, "new/nested/dir")
        assert result == "new/nested/dir"
        assert (tmp_path / "new" / "nested" / "dir").is_dir()
