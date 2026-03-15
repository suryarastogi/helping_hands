"""Tests for v205 DRY improvements.

Covers:
- _validate_script_path helper in command.py
- _display_path helper in filesystem.py
- install_hint usage in AI provider error messages
- KEYCHAIN_TIMEOUT_S / USAGE_API_TIMEOUT_S in server/constants.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from helping_hands.lib.ai_providers.anthropic import AnthropicProvider
from helping_hands.lib.ai_providers.google import GoogleProvider
from helping_hands.lib.ai_providers.litellm import LiteLLMProvider
from helping_hands.lib.ai_providers.ollama import OllamaProvider
from helping_hands.lib.ai_providers.openai import OpenAIProvider
from helping_hands.lib.meta.tools.command import (
    _validate_script_path,
    run_bash_script,
    run_python_script,
)
from helping_hands.lib.meta.tools.filesystem import (
    _display_path,
    mkdir_path,
    read_text_file,
    write_text_file,
)
from helping_hands.server.constants import KEYCHAIN_TIMEOUT_S, USAGE_API_TIMEOUT_S


def _can_import(name: str) -> bool:
    """Check if a module can be imported without side effects."""
    try:
        __import__(name)
        return True
    except ImportError:
        return False


_has_fastapi = _can_import("fastapi")
_has_celery = _can_import("celery")


# ---------------------------------------------------------------------------
# command.py: _validate_script_path
# ---------------------------------------------------------------------------


class TestValidateScriptPath:
    """Tests for the extracted _validate_script_path helper."""

    def test_returns_resolved_path(self, tmp_path: Path) -> None:
        script = tmp_path / "hello.py"
        script.write_text("print('hi')")
        result = _validate_script_path(tmp_path, "hello.py")
        assert result == script.resolve()

    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="script not found"):
            _validate_script_path(tmp_path, "missing.py")

    def test_raises_is_a_directory(self, tmp_path: Path) -> None:
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        with pytest.raises(IsADirectoryError, match="script path is a directory"):
            _validate_script_path(tmp_path, "subdir")

    def test_run_python_script_uses_validate(self, tmp_path: Path) -> None:
        """run_python_script delegates to _validate_script_path for missing scripts."""
        with pytest.raises(FileNotFoundError, match="script not found"):
            run_python_script(tmp_path, script_path="nonexistent.py")

    def test_run_bash_script_uses_validate(self, tmp_path: Path) -> None:
        """run_bash_script delegates to _validate_script_path for missing scripts."""
        with pytest.raises(FileNotFoundError, match="script not found"):
            run_bash_script(tmp_path, script_path="nonexistent.sh")

    def test_run_python_script_dir_error(self, tmp_path: Path) -> None:
        subdir = tmp_path / "pkg"
        subdir.mkdir()
        with pytest.raises(IsADirectoryError, match="script path is a directory"):
            run_python_script(tmp_path, script_path="pkg")

    def test_run_bash_script_dir_error(self, tmp_path: Path) -> None:
        subdir = tmp_path / "pkg"
        subdir.mkdir()
        with pytest.raises(IsADirectoryError, match="script path is a directory"):
            run_bash_script(tmp_path, script_path="pkg")


# ---------------------------------------------------------------------------
# filesystem.py: _display_path
# ---------------------------------------------------------------------------


class TestDisplayPath:
    """Tests for the extracted _display_path helper."""

    def test_simple_relative(self, tmp_path: Path) -> None:
        target = tmp_path / "foo" / "bar.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        result = _display_path(target, tmp_path)
        assert result == "foo/bar.txt"

    def test_single_file(self, tmp_path: Path) -> None:
        target = tmp_path / "readme.md"
        result = _display_path(target, tmp_path)
        assert result == "readme.md"

    def test_read_text_file_uses_display_path(self, tmp_path: Path) -> None:
        """read_text_file returns display path via _display_path."""
        f = tmp_path / "test.txt"
        f.write_text("hello")
        _, _, display = read_text_file(tmp_path, "test.txt")
        assert display == "test.txt"

    def test_write_text_file_uses_display_path(self, tmp_path: Path) -> None:
        """write_text_file returns display path via _display_path."""
        result = write_text_file(tmp_path, "sub/out.txt", "data")
        assert result == "sub/out.txt"

    def test_mkdir_path_uses_display_path(self, tmp_path: Path) -> None:
        """mkdir_path returns display path via _display_path."""
        result = mkdir_path(tmp_path, "new/dir")
        assert result == "new/dir"

    def test_read_text_file_not_found_includes_display(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match=r"file not found: nope\.txt"):
            read_text_file(tmp_path, "nope.txt")

    def test_read_text_file_is_dir_includes_display(self, tmp_path: Path) -> None:
        subdir = tmp_path / "adir"
        subdir.mkdir()
        with pytest.raises(IsADirectoryError, match="path is a directory: adir"):
            read_text_file(tmp_path, "adir")


# ---------------------------------------------------------------------------
# AI providers: install_hint in error messages
# ---------------------------------------------------------------------------


class TestProviderInstallHintInError:
    """Each provider's _build_inner error message should reference install_hint."""

    def test_anthropic_error_uses_install_hint(self) -> None:
        provider = AnthropicProvider()
        provider._inner = None
        with (
            patch.dict(sys.modules, {"anthropic": None}),
            pytest.raises(RuntimeError, match=provider.install_hint),
        ):
            _ = provider.inner

    def test_openai_error_uses_install_hint(self) -> None:
        provider = OpenAIProvider()
        provider._inner = None
        with (
            patch.dict(sys.modules, {"openai": None}),
            pytest.raises(RuntimeError, match=provider.install_hint),
        ):
            _ = provider.inner

    def test_google_error_uses_install_hint(self) -> None:
        provider = GoogleProvider()
        provider._inner = None
        with (
            patch.dict(sys.modules, {"google": None}),
            pytest.raises(RuntimeError, match=provider.install_hint),
        ):
            _ = provider.inner

    def test_litellm_error_uses_install_hint(self) -> None:
        provider = LiteLLMProvider()
        provider._inner = None
        with (
            patch.dict(sys.modules, {"litellm": None}),
            pytest.raises(RuntimeError, match=provider.install_hint),
        ):
            _ = provider.inner

    def test_ollama_error_uses_install_hint(self) -> None:
        provider = OllamaProvider()
        provider._inner = None
        with (
            patch.dict(sys.modules, {"openai": None}),
            pytest.raises(RuntimeError, match=provider.install_hint),
        ):
            _ = provider.inner


# ---------------------------------------------------------------------------
# server/constants.py: shared timeout constants
# ---------------------------------------------------------------------------


class TestSharedTimeoutConstants:
    """Verify timeout constants exist in shared module with expected values."""

    def test_keychain_timeout_value(self) -> None:
        assert KEYCHAIN_TIMEOUT_S == 5

    def test_usage_api_timeout_value(self) -> None:
        assert USAGE_API_TIMEOUT_S == 10

    def test_keychain_timeout_is_int(self) -> None:
        assert isinstance(KEYCHAIN_TIMEOUT_S, int)

    def test_usage_api_timeout_is_int(self) -> None:
        assert isinstance(USAGE_API_TIMEOUT_S, int)


class TestTimeoutConstantsImported:
    """Verify app.py and celery_app.py import from constants, not define locally."""

    @pytest.mark.skipif(not _has_fastapi, reason="fastapi not installed")
    def test_app_imports_keychain_timeout(self) -> None:
        from helping_hands.server import app

        assert app._KEYCHAIN_TIMEOUT_S == KEYCHAIN_TIMEOUT_S

    @pytest.mark.skipif(not _has_fastapi, reason="fastapi not installed")
    def test_app_imports_usage_api_timeout(self) -> None:
        from helping_hands.server import app

        assert app._USAGE_API_TIMEOUT_S == USAGE_API_TIMEOUT_S

    @pytest.mark.skipif(not _has_celery, reason="celery not installed")
    def test_celery_imports_keychain_timeout(self) -> None:
        from helping_hands.server import celery_app

        assert celery_app._KEYCHAIN_TIMEOUT_S == KEYCHAIN_TIMEOUT_S

    @pytest.mark.skipif(not _has_celery, reason="celery not installed")
    def test_celery_imports_usage_api_timeout(self) -> None:
        from helping_hands.server import celery_app

        assert celery_app._USAGE_API_TIMEOUT_S == USAGE_API_TIMEOUT_S
