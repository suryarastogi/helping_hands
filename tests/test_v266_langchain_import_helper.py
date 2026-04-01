"""Guards that missing optional LangChain extras produce actionable install
instructions instead of opaque import tracebacks.

_require_langchain_class() must auto-derive the package name from the module
path (langchain_foo_bar -> "uv add langchain-foo-bar") so new providers get
correct hints without manual wiring. The explicit-install override must work
for multi-package cases like langchain-community+litellm. The RuntimeError
must chain the original ModuleNotFoundError so debugging context is preserved.
Without this guard, users who run --backend basic-langgraph without the extra
see an AttributeError deep in the LangChain call stack.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from helping_hands.lib.hands.v1.hand.model_provider import (
    _require_langchain_class,
)

# ---------------------------------------------------------------------------
# _require_langchain_class() unit tests
# ---------------------------------------------------------------------------


class TestRequireLangchainClass:
    """Tests for the _require_langchain_class() import helper."""

    def test_returns_class_when_module_present(self) -> None:
        """Successful import returns the requested class."""

        class FakeChat:
            pass

        fake_mod = SimpleNamespace(FakeChat=FakeChat)
        with patch.dict("sys.modules", {"fake_langchain": fake_mod}):
            result = _require_langchain_class("fake_langchain", "FakeChat", hint="test")
        assert result is FakeChat

    def test_raises_runtime_error_when_module_missing(self) -> None:
        """Missing module raises RuntimeError with hint and install command."""
        with (
            patch.dict("sys.modules", {"langchain_missing": None}),
            pytest.raises(RuntimeError, match="test hint") as exc_info,
        ):
            _require_langchain_class("langchain_missing", "SomeClass", hint="test hint")
        assert "uv add langchain-missing" in str(exc_info.value)

    def test_auto_derives_install_from_module_path(self) -> None:
        """When install is None, derives package name from module_path."""
        with (
            patch.dict("sys.modules", {"langchain_foo_bar": None}),
            pytest.raises(RuntimeError) as exc_info,
        ):
            _require_langchain_class("langchain_foo_bar", "Cls", hint="need foo")
        assert "uv add langchain-foo-bar" in str(exc_info.value)

    def test_explicit_install_overrides_auto_derive(self) -> None:
        """When install is provided, it is used verbatim."""
        with (
            patch.dict("sys.modules", {"langchain_community.chat_models": None}),
            pytest.raises(RuntimeError) as exc_info,
        ):
            _require_langchain_class(
                "langchain_community.chat_models",
                "ChatLiteLLM",
                hint="litellm models require langchain-community and litellm",
                install="langchain-community litellm",
            )
        assert "uv add langchain-community litellm" in str(exc_info.value)

    def test_chained_exception_is_module_not_found(self) -> None:
        """The RuntimeError chains the original ModuleNotFoundError."""
        with (
            patch.dict("sys.modules", {"langchain_gone": None}),
            pytest.raises(RuntimeError) as exc_info,
        ):
            _require_langchain_class("langchain_gone", "X", hint="gone")
        assert isinstance(exc_info.value.__cause__, ModuleNotFoundError)

    def test_hint_appears_in_message(self) -> None:
        """The hint text appears at the start of the error message."""
        with (
            patch.dict("sys.modules", {"langchain_nope": None}),
            pytest.raises(RuntimeError, match=r"^custom hint") as exc_info,
        ):
            _require_langchain_class("langchain_nope", "Y", hint="custom hint")
        msg = str(exc_info.value)
        assert msg.startswith("custom hint")

    def test_submodule_import(self) -> None:
        """Dotted module paths (submodules) are handled correctly."""

        class SubChat:
            pass

        sub_mod = SimpleNamespace(SubChat=SubChat)
        parent = SimpleNamespace()
        with patch.dict(
            "sys.modules",
            {"langchain_parent": parent, "langchain_parent.sub": sub_mod},
        ):
            result = _require_langchain_class(
                "langchain_parent.sub", "SubChat", hint="test"
            )
        assert result is SubChat


# ---------------------------------------------------------------------------
# Integration: build_langchain_chat_model uses _require_langchain_class
# ---------------------------------------------------------------------------


class TestBuildLangchainUsesHelper:
    """Verify build_langchain_chat_model delegates to _require_langchain_class."""

    def test_anthropic_error_message_format(self) -> None:
        """Anthropic import failure includes install hint."""
        from helping_hands.lib.ai_providers import PROVIDERS
        from helping_hands.lib.hands.v1.hand.model_provider import (
            HandModel,
            build_langchain_chat_model,
        )

        hm = HandModel(
            provider=PROVIDERS["anthropic"], model="claude-sonnet-4-5", raw="test"
        )
        with (
            patch.dict("sys.modules", {"langchain_anthropic": None}),
            pytest.raises(RuntimeError, match="uv add langchain-anthropic"),
        ):
            build_langchain_chat_model(hm, streaming=True)

    def test_google_error_message_format(self) -> None:
        """Google import failure includes install hint."""
        from helping_hands.lib.ai_providers import PROVIDERS
        from helping_hands.lib.hands.v1.hand.model_provider import (
            HandModel,
            build_langchain_chat_model,
        )

        hm = HandModel(
            provider=PROVIDERS["google"], model="gemini-2.0-flash", raw="test"
        )
        with (
            patch.dict("sys.modules", {"langchain_google_genai": None}),
            pytest.raises(RuntimeError, match="uv add langchain-google-genai"),
        ):
            build_langchain_chat_model(hm, streaming=False)

    def test_litellm_error_message_format(self) -> None:
        """LiteLLM import failure includes explicit install packages."""
        from helping_hands.lib.ai_providers import PROVIDERS
        from helping_hands.lib.hands.v1.hand.model_provider import (
            HandModel,
            build_langchain_chat_model,
        )

        hm = HandModel(provider=PROVIDERS["litellm"], model="gpt-5.2", raw="test")
        with (
            patch.dict(
                "sys.modules",
                {
                    "langchain_community": None,
                    "langchain_community.chat_models": None,
                },
            ),
            pytest.raises(RuntimeError, match="uv add langchain-community litellm"),
        ):
            build_langchain_chat_model(hm, streaming=False)


# ---------------------------------------------------------------------------
# __all__ export
# ---------------------------------------------------------------------------


class TestExport:  # TODO: CLEANUP CANDIDATE — stylistic __all__ check, no behavioral invariant
    """Verify _require_langchain_class is exported."""

    def test_in_all(self) -> None:
        from helping_hands.lib.hands.v1.hand import model_provider

        assert "_require_langchain_class" in model_provider.__all__
