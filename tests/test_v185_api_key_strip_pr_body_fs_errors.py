"""Tests for v185: API key whitespace stripping, _build_generic_pr_body
validation for commit_sha/stamp_utc, and filesystem error messages with
path context."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.ai_providers.anthropic import AnthropicProvider
from helping_hands.lib.ai_providers.google import GoogleProvider
from helping_hands.lib.ai_providers.litellm import LiteLLMProvider
from helping_hands.lib.ai_providers.ollama import OllamaProvider
from helping_hands.lib.ai_providers.openai import OpenAIProvider

# ---------------------------------------------------------------------------
# API key whitespace stripping — all providers
# ---------------------------------------------------------------------------


class TestOpenAIApiKeyWhitespaceStrip:
    """OpenAIProvider._build_inner() strips whitespace from API key env var."""

    def _make_openai_module(self) -> ModuleType:
        mod = ModuleType("openai")
        mod.OpenAI = MagicMock()  # type: ignore[attr-defined]
        return mod

    def test_whitespace_only_key_creates_client_without_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "   ")
        mod = self._make_openai_module()
        with patch.dict(sys.modules, {"openai": mod}):
            provider = OpenAIProvider()
            provider._inner = None
            _ = provider.inner
        mod.OpenAI.assert_called_once_with()  # type: ignore[attr-defined]

    def test_valid_key_with_whitespace_is_stripped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "  sk-test  ")
        mod = self._make_openai_module()
        with patch.dict(sys.modules, {"openai": mod}):
            provider = OpenAIProvider()
            provider._inner = None
            _ = provider.inner
        mod.OpenAI.assert_called_once_with(api_key="sk-test")  # type: ignore[attr-defined]


class TestAnthropicApiKeyWhitespaceStrip:
    """AnthropicProvider._build_inner() strips whitespace from API key."""

    def _make_anthropic_module(self) -> ModuleType:
        mod = ModuleType("anthropic")
        mod.Anthropic = MagicMock()  # type: ignore[attr-defined]
        return mod

    def test_whitespace_only_key_creates_client_without_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "  \t  ")
        mod = self._make_anthropic_module()
        with patch.dict(sys.modules, {"anthropic": mod}):
            provider = AnthropicProvider()
            provider._inner = None
            _ = provider.inner
        mod.Anthropic.assert_called_once_with()  # type: ignore[attr-defined]

    def test_valid_key_with_whitespace_is_stripped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", " sk-ant-test ")
        mod = self._make_anthropic_module()
        with patch.dict(sys.modules, {"anthropic": mod}):
            provider = AnthropicProvider()
            provider._inner = None
            _ = provider.inner
        mod.Anthropic.assert_called_once_with(api_key="sk-ant-test")  # type: ignore[attr-defined]


class TestGoogleApiKeyWhitespaceStrip:
    """GoogleProvider._build_inner() strips whitespace from API key."""

    def _make_google_modules(self) -> tuple[ModuleType, MagicMock]:
        fake_client_cls = MagicMock()
        fake_genai = ModuleType("genai")
        fake_genai.Client = fake_client_cls  # type: ignore[attr-defined]
        fake_google = ModuleType("google")
        fake_google.genai = fake_genai  # type: ignore[attr-defined]
        return fake_google, fake_client_cls

    def test_whitespace_only_key_creates_client_without_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_API_KEY", "   ")
        fake_google, fake_client_cls = self._make_google_modules()
        with patch.dict(
            sys.modules,
            {"google": fake_google, "google.genai": fake_google.genai},  # type: ignore[attr-defined]
        ):
            provider = GoogleProvider()
            provider._inner = None
            _ = provider.inner
        fake_client_cls.assert_called_once_with()

    def test_valid_key_with_whitespace_is_stripped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_API_KEY", " AIza-test ")
        fake_google, fake_client_cls = self._make_google_modules()
        with patch.dict(
            sys.modules,
            {"google": fake_google, "google.genai": fake_google.genai},  # type: ignore[attr-defined]
        ):
            provider = GoogleProvider()
            provider._inner = None
            _ = provider.inner
        fake_client_cls.assert_called_once_with(api_key="AIza-test")


class TestLiteLLMApiKeyWhitespaceStrip:
    """LiteLLMProvider._build_inner() strips whitespace from API key."""

    def test_whitespace_only_key_does_not_set_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LITELLM_API_KEY", "   ")
        fake_module = ModuleType("litellm")
        fake_module.api_key = None  # type: ignore[attr-defined]
        with patch.dict(sys.modules, {"litellm": fake_module}):
            provider = LiteLLMProvider()
            provider._inner = None
            _ = provider.inner
        assert fake_module.api_key is None  # type: ignore[attr-defined]

    def test_valid_key_with_whitespace_is_stripped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LITELLM_API_KEY", " lt-test ")
        fake_module = ModuleType("litellm")
        fake_module.api_key = None  # type: ignore[attr-defined]
        with patch.dict(sys.modules, {"litellm": fake_module}):
            provider = LiteLLMProvider()
            provider._inner = None
            _ = provider.inner
        assert fake_module.api_key == "lt-test"  # type: ignore[attr-defined]


class TestOllamaApiKeyWhitespaceStrip:
    """OllamaProvider._build_inner() strips whitespace; falls back to defaults."""

    def _make_openai_module(self) -> ModuleType:
        mod = ModuleType("openai")
        mod.OpenAI = MagicMock()  # type: ignore[attr-defined]
        return mod

    def test_whitespace_only_key_falls_back_to_ollama(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OLLAMA_API_KEY", "   ")
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        mod = self._make_openai_module()
        with patch.dict(sys.modules, {"openai": mod}):
            provider = OllamaProvider()
            provider._inner = None
            _ = provider.inner
        call_kwargs = mod.OpenAI.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs["api_key"] == "ollama"

    def test_whitespace_only_base_url_falls_back_to_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OLLAMA_BASE_URL", "  ")
        monkeypatch.setenv("OLLAMA_API_KEY", "key")
        mod = self._make_openai_module()
        with patch.dict(sys.modules, {"openai": mod}):
            provider = OllamaProvider()
            provider._inner = None
            _ = provider.inner
        call_kwargs = mod.OpenAI.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs["base_url"] == OllamaProvider.default_base_url


# ---------------------------------------------------------------------------
# _build_generic_pr_body — commit_sha and stamp_utc validation
# ---------------------------------------------------------------------------


class TestBuildGenericPrBodyValidation:
    """_build_generic_pr_body() validates commit_sha and stamp_utc."""

    def test_empty_commit_sha_raises_value_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        with pytest.raises(ValueError, match="commit_sha must be a non-empty string"):
            Hand._build_generic_pr_body(
                backend="test",
                prompt="do stuff",
                summary="",
                commit_sha="",
                stamp_utc="2026-01-01T00:00:00",
            )

    def test_whitespace_commit_sha_raises_value_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        with pytest.raises(ValueError, match="commit_sha must be a non-empty string"):
            Hand._build_generic_pr_body(
                backend="test",
                prompt="do stuff",
                summary="",
                commit_sha="   ",
                stamp_utc="2026-01-01T00:00:00",
            )

    def test_non_string_commit_sha_raises_value_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        with pytest.raises(ValueError, match="commit_sha must be a non-empty string"):
            Hand._build_generic_pr_body(
                backend="test",
                prompt="do stuff",
                summary="",
                commit_sha=123,  # type: ignore[arg-type]
                stamp_utc="2026-01-01T00:00:00",
            )

    def test_empty_stamp_utc_raises_value_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        with pytest.raises(ValueError, match="stamp_utc must be a non-empty string"):
            Hand._build_generic_pr_body(
                backend="test",
                prompt="do stuff",
                summary="",
                commit_sha="abc123",
                stamp_utc="",
            )

    def test_whitespace_stamp_utc_raises_value_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        with pytest.raises(ValueError, match="stamp_utc must be a non-empty string"):
            Hand._build_generic_pr_body(
                backend="test",
                prompt="do stuff",
                summary="",
                commit_sha="abc123",
                stamp_utc="  \t  ",
            )

    def test_non_string_stamp_utc_raises_value_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        with pytest.raises(ValueError, match="stamp_utc must be a non-empty string"):
            Hand._build_generic_pr_body(
                backend="test",
                prompt="do stuff",
                summary="",
                commit_sha="abc123",
                stamp_utc=None,  # type: ignore[arg-type]
            )

    def test_valid_params_produce_expected_body(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        body = Hand._build_generic_pr_body(
            backend="claudecodecli",
            prompt="add tests",
            summary="Added unit tests",
            commit_sha="abc123def",
            stamp_utc="2026-03-15T12:00:00+00:00",
        )
        assert "abc123def" in body
        assert "2026-03-15T12:00:00+00:00" in body
        assert "Added unit tests" in body


# ---------------------------------------------------------------------------
# Filesystem error messages — path context included
# ---------------------------------------------------------------------------


class TestReadTextFileErrorMessages:
    """read_text_file() includes path context in error messages."""

    def test_file_not_found_includes_path(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.filesystem import read_text_file

        with pytest.raises(FileNotFoundError, match=r"nonexistent\.txt"):
            read_text_file(tmp_path, "nonexistent.txt")

    def test_is_a_directory_includes_path(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.filesystem import read_text_file

        subdir = tmp_path / "mydir"
        subdir.mkdir()
        with pytest.raises(IsADirectoryError, match="mydir"):
            read_text_file(tmp_path, "mydir")

    def test_nested_path_in_error_message(self, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.filesystem import read_text_file

        (tmp_path / "deep" / "nested").mkdir(parents=True)
        with pytest.raises(FileNotFoundError, match=r"deep/nested/file\.txt"):
            read_text_file(tmp_path, "deep/nested/file.txt")
