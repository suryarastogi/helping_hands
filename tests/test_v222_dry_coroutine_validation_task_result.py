"""Tests for v222: DRY _close_coroutine, model_provider validation, task_result hardening."""

from __future__ import annotations

import ast
import contextlib
import inspect
import warnings
from unittest.mock import MagicMock

import pytest

from helping_hands.lib.hands.v1.hand.model_provider import (
    HandModel,
    build_atomic_client,
    build_langchain_chat_model,
)
from helping_hands.server.task_result import normalize_task_result

# ---------------------------------------------------------------------------
# DRY _close_coroutine — module-level helper in test_cli.py
# ---------------------------------------------------------------------------


class TestCloseCoroutineExtraction:
    """Verify that _close_coroutine is a single module-level function in test_cli.py."""

    def test_module_level_definition_exists(self) -> None:
        """_close_coroutine should be importable from test_cli."""
        from tests.test_cli import _close_coroutine

        assert callable(_close_coroutine)

    def test_has_docstring(self) -> None:
        from tests.test_cli import _close_coroutine

        assert _close_coroutine.__doc__ is not None

    def test_no_inline_definitions(self) -> None:
        """No class or method should define _close_coroutine locally."""
        import tests.test_cli as mod

        source = inspect.getsource(mod)
        tree = ast.parse(source)
        inline_defs = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.FunctionDef)
                        and child.name == "_close_coroutine"
                        and child is not node
                    ):
                        inline_defs.append(child.lineno)
        assert inline_defs == [], (
            f"Found inline _close_coroutine definitions at lines: {inline_defs}"
        )

    def test_closes_coroutine_object(self) -> None:
        """_close_coroutine should call .close() on coroutine-like objects."""
        from tests.test_cli import _close_coroutine

        mock_coro = MagicMock()
        _close_coroutine(mock_coro)
        mock_coro.close.assert_called_once()

    def test_handles_non_coroutine(self) -> None:
        """_close_coroutine should handle objects without .close()."""
        from tests.test_cli import _close_coroutine

        _close_coroutine(42)  # should not raise

    def test_closes_real_coroutine(self) -> None:
        """_close_coroutine should properly finalize a real coroutine."""
        from tests.test_cli import _close_coroutine

        async def _dummy() -> None:
            pass

        coro = _dummy()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _close_coroutine(coro)
        runtime_warnings = [w for w in caught if issubclass(w.category, RuntimeWarning)]
        assert runtime_warnings == []

    def test_pytestmark_suppresses_coroutine_warning(self) -> None:
        """test_cli.py should have a pytestmark that filters coroutine warnings."""
        import tests.test_cli as mod

        marks = getattr(mod, "pytestmark", None)
        assert marks is not None, "test_cli.py should define pytestmark"


# ---------------------------------------------------------------------------
# model_provider.py — build_* input validation
# ---------------------------------------------------------------------------


class TestBuildLangchainValidation:
    """build_langchain_chat_model rejects empty/whitespace model strings."""

    def test_empty_model_raises(self) -> None:
        provider = MagicMock()
        provider.name = "openai"
        hm = HandModel(provider=provider, model="", raw="")
        with pytest.raises(ValueError, match=r"hand_model\.model"):
            build_langchain_chat_model(hm, streaming=False)

    def test_whitespace_model_raises(self) -> None:
        provider = MagicMock()
        provider.name = "openai"
        hm = HandModel(provider=provider, model="   ", raw="   ")
        with pytest.raises(ValueError, match=r"hand_model\.model"):
            build_langchain_chat_model(hm, streaming=False)

    def test_valid_model_passes_through(self) -> None:
        """A non-empty model should proceed to the provider import."""
        provider = MagicMock()
        provider.name = "openai"
        hm = HandModel(provider=provider, model="gpt-4", raw="gpt-4")
        with contextlib.suppress(ModuleNotFoundError, ImportError):
            build_langchain_chat_model(hm, streaming=True)


class TestBuildAtomicValidation:
    """build_atomic_client rejects empty/whitespace model strings."""

    def test_empty_model_raises(self) -> None:
        provider = MagicMock()
        provider.name = "openai"
        hm = HandModel(provider=provider, model="", raw="")
        with pytest.raises(ValueError, match=r"hand_model\.model"):
            build_atomic_client(hm)

    def test_whitespace_model_raises(self) -> None:
        provider = MagicMock()
        provider.name = "openai"
        hm = HandModel(provider=provider, model="  \t  ", raw="  ")
        with pytest.raises(ValueError, match=r"hand_model\.model"):
            build_atomic_client(hm)


# ---------------------------------------------------------------------------
# task_result.py — status validation + JSON-safe serialization
# ---------------------------------------------------------------------------


class TestTaskResultStatusValidation:
    """normalize_task_result rejects empty/whitespace status."""

    def test_empty_status_raises(self) -> None:
        with pytest.raises(ValueError, match="status"):
            normalize_task_result("", {"ok": True})

    def test_whitespace_status_raises(self) -> None:
        with pytest.raises(ValueError, match="status"):
            normalize_task_result("   ", {"ok": True})

    def test_valid_status_on_none_result(self) -> None:
        assert normalize_task_result("PENDING", None) is None


class TestTaskResultJsonSafe:
    """normalize_task_result preserves JSON-serializable types."""

    def test_int_preserved(self) -> None:
        result = normalize_task_result("SUCCESS", 42)
        assert result is not None
        assert result["value"] == 42
        assert isinstance(result["value"], int)

    def test_float_preserved(self) -> None:
        result = normalize_task_result("SUCCESS", 3.14)
        assert result is not None
        assert result["value"] == 3.14

    def test_list_preserved(self) -> None:
        result = normalize_task_result("SUCCESS", [1, "two", 3])
        assert result is not None
        assert result["value"] == [1, "two", 3]
        assert isinstance(result["value"], list)

    def test_bool_preserved(self) -> None:
        result = normalize_task_result("SUCCESS", True)
        assert result is not None
        assert result["value"] is True

    def test_nested_list_preserved(self) -> None:
        val = [[1, 2], [3, 4]]
        result = normalize_task_result("SUCCESS", val)
        assert result is not None
        assert result["value"] == [[1, 2], [3, 4]]

    def test_tuple_preserved_as_list(self) -> None:
        """Tuples are JSON-serializable (as lists)."""
        result = normalize_task_result("SUCCESS", (1, 2))
        assert result is not None
        # json.dumps((1,2)) works — value is the original tuple
        assert result["value"] == (1, 2)
        assert result["value_type"] == "tuple"

    def test_non_serializable_falls_back_to_str(self) -> None:
        """Objects that can't be JSON-serialized fall back to str()."""

        class Custom:
            def __str__(self) -> str:
                return "custom-repr"

        result = normalize_task_result("SUCCESS", Custom())
        assert result is not None
        assert result["value"] == "custom-repr"
        assert result["value_type"] == "Custom"

    def test_bytes_falls_back_to_str(self) -> None:
        """Bytes are not JSON-serializable and should fall back to str()."""
        result = normalize_task_result("SUCCESS", b"hello")
        assert result is not None
        assert result["value"] == "b'hello'"
        assert result["value_type"] == "bytes"

    def test_set_falls_back_to_str(self) -> None:
        """Sets are not JSON-serializable."""
        result = normalize_task_result("SUCCESS", {1, 2})
        assert result is not None
        assert isinstance(result["value"], str)
        assert result["value_type"] == "set"


# ---------------------------------------------------------------------------
# Source consistency checks
# ---------------------------------------------------------------------------


class TestSourceConsistency:
    """Verify structural invariants in modified modules."""

    def test_model_provider_imports_validation(self) -> None:
        """model_provider.py should import require_non_empty_string."""
        import helping_hands.lib.hands.v1.hand.model_provider as mod

        source = inspect.getsource(mod)
        assert "require_non_empty_string" in source

    def test_task_result_imports_validation(self) -> None:
        """task_result.py should import require_non_empty_string."""
        import helping_hands.server.task_result as mod

        source = inspect.getsource(mod)
        assert "require_non_empty_string" in source

    def test_task_result_uses_json_dumps(self) -> None:
        """task_result.py should try json.dumps before str() fallback."""
        import helping_hands.server.task_result as mod

        source = inspect.getsource(mod)
        assert "json.dumps" in source

    def test_test_cli_no_duplicate_close_coroutine(self) -> None:
        """test_cli.py should have exactly one _close_coroutine definition."""
        import tests.test_cli as mod

        source = inspect.getsource(mod)
        count = source.count("def _close_coroutine(")
        assert count == 1, f"Expected 1 definition, found {count}"
