"""Tests for v226 — DRY _run_bash_script, prompt builder type guards."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from helping_hands.lib.hands.v1.hand.pr_description import (
    _build_commit_message_prompt,
    _build_prompt,
)
from helping_hands.lib.meta.tools.registry import _run_bash_script

# ---------------------------------------------------------------------------
# _run_bash_script — DRY via _parse_optional_str
# ---------------------------------------------------------------------------


class TestRunBashScriptDry:
    """Verify _run_bash_script uses _parse_optional_str for type validation."""

    def test_source_uses_parse_optional_str(self) -> None:
        """_run_bash_script delegates to _parse_optional_str, not manual isinstance."""
        source = inspect.getsource(_run_bash_script)
        assert "_parse_optional_str" in source
        assert "isinstance(script_path" not in source
        assert "isinstance(inline_script" not in source

    def test_rejects_non_string_script_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="script_path must be a string"):
            _run_bash_script(tmp_path, {"script_path": 42})

    def test_rejects_non_string_inline_script(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="inline_script must be a string"):
            _run_bash_script(tmp_path, {"inline_script": 99})

    def test_whitespace_only_script_path_treated_as_absent(
        self, tmp_path: Path
    ) -> None:
        """Whitespace-only script_path normalizes to None via _parse_optional_str."""
        with pytest.raises(ValueError, match="exactly one"):
            _run_bash_script(tmp_path, {"script_path": "   "})

    def test_whitespace_only_inline_script_treated_as_absent(
        self, tmp_path: Path
    ) -> None:
        """Whitespace-only inline_script normalizes to None via _parse_optional_str."""
        with pytest.raises(ValueError, match="exactly one"):
            _run_bash_script(tmp_path, {"inline_script": "   "})

    def test_rejects_bool_script_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="script_path must be a string"):
            _run_bash_script(tmp_path, {"script_path": True})

    def test_rejects_list_inline_script(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="inline_script must be a string"):
            _run_bash_script(tmp_path, {"inline_script": ["echo", "hi"]})


# ---------------------------------------------------------------------------
# _build_prompt — type guards
# ---------------------------------------------------------------------------


class TestBuildPromptTypeGuards:
    """Verify _build_prompt validates diff and backend with type guards."""

    def test_source_uses_require_non_empty_string(self) -> None:
        source = inspect.getsource(_build_prompt)
        assert "require_non_empty_string(diff" in source
        assert "require_non_empty_string(backend" in source

    def test_rejects_none_diff(self) -> None:
        with pytest.raises(TypeError, match="diff"):
            _build_prompt(
                diff=None,
                backend="test",
                user_prompt="p",
                summary="",  # type: ignore[arg-type]
            )

    def test_rejects_int_diff(self) -> None:
        with pytest.raises(TypeError, match="diff"):
            _build_prompt(
                diff=42,
                backend="test",
                user_prompt="p",
                summary="",  # type: ignore[arg-type]
            )

    def test_rejects_empty_diff(self) -> None:
        with pytest.raises(ValueError, match="diff"):
            _build_prompt(diff="", backend="test", user_prompt="p", summary="")

    def test_rejects_whitespace_only_diff(self) -> None:
        with pytest.raises(ValueError, match="diff"):
            _build_prompt(diff="   ", backend="test", user_prompt="p", summary="")

    def test_rejects_none_backend(self) -> None:
        with pytest.raises(TypeError, match="backend"):
            _build_prompt(
                diff="diff",
                backend=None,
                user_prompt="p",
                summary="",  # type: ignore[arg-type]
            )

    def test_rejects_int_backend(self) -> None:
        with pytest.raises(TypeError, match="backend"):
            _build_prompt(
                diff="diff",
                backend=123,
                user_prompt="p",
                summary="",  # type: ignore[arg-type]
            )

    def test_rejects_empty_backend(self) -> None:
        with pytest.raises(ValueError, match="backend"):
            _build_prompt(diff="diff", backend="", user_prompt="p", summary="")

    def test_valid_inputs_pass(self) -> None:
        result = _build_prompt(
            diff="diff content", backend="test", user_prompt="p", summary=""
        )
        assert "diff content" in result
        assert "test" in result


# ---------------------------------------------------------------------------
# _build_commit_message_prompt — type guards
# ---------------------------------------------------------------------------


class TestBuildCommitMessagePromptTypeGuards:
    """Verify _build_commit_message_prompt validates diff and backend."""

    def test_source_uses_require_non_empty_string(self) -> None:
        source = inspect.getsource(_build_commit_message_prompt)
        assert "require_non_empty_string(diff" in source
        assert "require_non_empty_string(backend" in source

    def test_rejects_none_diff(self) -> None:
        with pytest.raises(TypeError, match="diff"):
            _build_commit_message_prompt(
                diff=None,
                backend="test",
                user_prompt="p",
                summary="",  # type: ignore[arg-type]
            )

    def test_rejects_int_diff(self) -> None:
        with pytest.raises(TypeError, match="diff"):
            _build_commit_message_prompt(
                diff=42,
                backend="test",
                user_prompt="p",
                summary="",  # type: ignore[arg-type]
            )

    def test_rejects_empty_diff(self) -> None:
        with pytest.raises(ValueError, match="diff"):
            _build_commit_message_prompt(
                diff="", backend="test", user_prompt="p", summary=""
            )

    def test_rejects_none_backend(self) -> None:
        with pytest.raises(TypeError, match="backend"):
            _build_commit_message_prompt(
                diff="diff",
                backend=None,
                user_prompt="p",
                summary="",  # type: ignore[arg-type]
            )

    def test_rejects_empty_backend(self) -> None:
        with pytest.raises(ValueError, match="backend"):
            _build_commit_message_prompt(
                diff="diff", backend="", user_prompt="p", summary=""
            )

    def test_valid_inputs_pass(self) -> None:
        result = _build_commit_message_prompt(
            diff="diff content", backend="test", user_prompt="p", summary=""
        )
        assert "diff content" in result
        assert "test" in result
