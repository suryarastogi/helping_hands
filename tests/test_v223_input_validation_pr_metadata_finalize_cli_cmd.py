"""Tests for v223: input validation at PR metadata, finalization, and CLI command entry.

These tests protect three validation boundaries that sit at the start of
expensive or irreversible operations. If _pr_result_metadata stops rejecting
empty fields, downstream code receives a result dict with blank PR URL or
branch and the UI/API silently returns unusable data. If _finalize_repo_pr
stops rejecting empty backend/prompt, it proceeds with a git commit carrying
no meaningful context. If _invoke_cli_with_cmd stops rejecting an empty command
list, subprocess.run raises an obscure OSError instead of a clear ValueError.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from helping_hands.lib.hands.v1.hand.base import Hand, PRStatus
from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

# ---------------------------------------------------------------------------
# Concrete Hand stub for _finalize_repo_pr testing
# ---------------------------------------------------------------------------


class _ConcreteHand(Hand):
    """Minimal concrete Hand subclass for testing base class methods."""

    async def run(self, prompt: str) -> dict:  # type: ignore[override]
        return {}

    async def stream(self, prompt: str) -> AsyncIterator[str]:  # type: ignore[override]
        yield ""


# ---------------------------------------------------------------------------
# Concrete CLI stub for _invoke_cli_with_cmd testing
# ---------------------------------------------------------------------------


class _CLIStub(_TwoPhaseCLIHand):
    _CLI_LABEL = "stub"
    _CLI_DISPLAY_NAME = "Stub CLI"
    _BACKEND_NAME = "stub-backend"
    _COMMAND_ENV_VAR = "STUB_CLI_CMD"
    _DEFAULT_CLI_CMD = "stub-cli -p"
    _DEFAULT_MODEL = "stub-model-1"
    _DEFAULT_APPEND_ARGS: tuple[str, ...] = ()
    _CONTAINER_ENABLED_ENV_VAR = ""
    _CONTAINER_IMAGE_ENV_VAR = ""
    _SUMMARY_CHAR_LIMIT = 6000


def _make_cli_stub() -> _CLIStub:
    stub = object.__new__(_CLIStub)
    stub._interrupt_event = MagicMock()
    stub._interrupt_event.is_set.return_value = False
    stub.config = SimpleNamespace(model="default", verbose=False)
    stub.repo_index = MagicMock()
    stub.repo_index.root.resolve.return_value = "/fake/repo"
    return stub


# ---------------------------------------------------------------------------
# _pr_result_metadata — empty field rejection
# ---------------------------------------------------------------------------

_VALID_META_KWARGS: dict[str, str] = {
    "pr_url": "https://github.com/o/r/pull/1",
    "pr_number": "1",
    "pr_branch": "helping-hands/test-abc",
    "pr_commit": "deadbeef",
}


class TestPrResultMetadataValidation:
    """Verify _pr_result_metadata rejects empty/whitespace string fields."""

    @pytest.mark.parametrize("field", ["pr_url", "pr_number", "pr_branch", "pr_commit"])
    def test_empty_string_raises(self, field: str) -> None:
        kwargs = {**_VALID_META_KWARGS, field: ""}
        with pytest.raises(ValueError, match=field):
            Hand._pr_result_metadata({}, status=PRStatus.CREATED, **kwargs)  # type: ignore[arg-type]

    @pytest.mark.parametrize("field", ["pr_url", "pr_number", "pr_branch", "pr_commit"])
    def test_whitespace_only_raises(self, field: str) -> None:
        kwargs = {**_VALID_META_KWARGS, field: "   "}
        with pytest.raises(ValueError, match=field):
            Hand._pr_result_metadata({}, status=PRStatus.CREATED, **kwargs)  # type: ignore[arg-type]

    def test_valid_fields_pass(self) -> None:
        result = Hand._pr_result_metadata(
            {},
            status=PRStatus.CREATED,
            **_VALID_META_KWARGS,  # type: ignore[arg-type]
        )
        assert result["pr_url"] == "https://github.com/o/r/pull/1"
        assert result["pr_number"] == "1"
        assert result["pr_branch"] == "helping-hands/test-abc"
        assert result["pr_commit"] == "deadbeef"


# ---------------------------------------------------------------------------
# _finalize_repo_pr — empty input rejection
# ---------------------------------------------------------------------------


class TestFinalizePrValidation:
    """Verify _finalize_repo_pr rejects empty/whitespace backend and prompt.

    Note: summary is intentionally *not* validated because the AI backend
    may produce an empty summary (e.g. empty messages list), and
    ``_build_generic_pr_body`` already has a fallback for that case.
    """

    def _make_hand(self) -> _ConcreteHand:
        hand = object.__new__(_ConcreteHand)
        return hand

    def test_empty_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="backend"):
            self._make_hand()._finalize_repo_pr(
                backend="", prompt="do x", summary="did x"
            )

    def test_whitespace_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="backend"):
            self._make_hand()._finalize_repo_pr(
                backend="  ", prompt="do x", summary="did x"
            )

    def test_empty_prompt_raises(self) -> None:
        with pytest.raises(ValueError, match="prompt"):
            self._make_hand()._finalize_repo_pr(
                backend="basic", prompt="", summary="did x"
            )

    def test_whitespace_prompt_raises(self) -> None:
        with pytest.raises(ValueError, match="prompt"):
            self._make_hand()._finalize_repo_pr(
                backend="basic", prompt="  \t", summary="did x"
            )


# ---------------------------------------------------------------------------
# _invoke_cli_with_cmd — empty command rejection
# ---------------------------------------------------------------------------


class TestInvokeCliWithCmdValidation:
    """Verify _invoke_cli_with_cmd rejects empty command lists."""

    def test_empty_list_raises(self) -> None:
        stub = _make_cli_stub()
        emit = MagicMock()
        with pytest.raises(ValueError, match="cmd must be a non-empty list"):
            asyncio.run(stub._invoke_cli_with_cmd([], emit=emit))

    def test_empty_first_element_raises(self) -> None:
        stub = _make_cli_stub()
        emit = MagicMock()
        with pytest.raises(ValueError, match="cmd must be a non-empty list"):
            asyncio.run(stub._invoke_cli_with_cmd([""], emit=emit))

    def test_none_first_element_raises(self) -> None:
        stub = _make_cli_stub()
        emit = MagicMock()
        with pytest.raises(ValueError, match="cmd must be a non-empty list"):
            asyncio.run(stub._invoke_cli_with_cmd([None], emit=emit))  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# Source consistency — ensure validation calls are present in source
# ---------------------------------------------------------------------------


class TestSourceConsistency:
    """Verify validation calls exist in source code."""

    def test_pr_result_metadata_has_validation(self) -> None:
        src = inspect.getsource(Hand._pr_result_metadata)
        assert "require_non_empty_string" in src
        for field in ("pr_url", "pr_number", "pr_branch", "pr_commit"):
            assert field in src

    def test_finalize_repo_pr_has_validation(self) -> None:
        src = inspect.getsource(Hand._finalize_repo_pr)
        assert "require_non_empty_string" in src
        for param in ("backend", "prompt"):
            assert f'"{param}"' in src

    def test_invoke_cli_with_cmd_has_validation(self) -> None:
        src = inspect.getsource(_TwoPhaseCLIHand._invoke_cli_with_cmd)
        assert "not cmd" in src

    def test_invoke_cli_with_cmd_has_docstring(self) -> None:
        doc = _TwoPhaseCLIHand._invoke_cli_with_cmd.__doc__
        assert doc is not None
        assert "cmd" in doc.lower()
