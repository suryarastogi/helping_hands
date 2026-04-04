"""Tests for helping_hands.lib.hands.v1.hand.model_provider.

Protects the model-resolution logic that converts bare model strings like
"gpt-5.2" or "claude-3-5-sonnet" into a (provider, model) pair consumed by
every Hand backend. Regressions in _infer_provider_name or resolve_hand_model
would route requests to the wrong AI provider, causing silent auth failures or
wrong-model responses. Also tests build_langchain_chat_model and
build_atomic_client to ensure each provider's lazy-import path raises a clear
RuntimeError when the optional package is absent rather than an AttributeError.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.model_provider import (
    _OLLAMA_MODEL_PREFIXES,
    _OPENAI_MODEL_PREFIXES,
    HandModel,
    _infer_provider_name,
    _require_langchain_class,
    build_atomic_client,
    build_langchain_chat_model,
    resolve_hand_model,
)

# ---------------------------------------------------------------------------
# _infer_provider_name
# ---------------------------------------------------------------------------


class TestInferProviderName:
    def test_claude_prefix_returns_anthropic(self) -> None:
        assert _infer_provider_name("claude-3-5-sonnet") == "anthropic"

    def test_claude_case_insensitive(self) -> None:
        assert _infer_provider_name("Claude-Opus") == "anthropic"
        assert _infer_provider_name("CLAUDE-HAIKU") == "anthropic"

    def test_gemini_prefix_returns_google(self) -> None:
        assert _infer_provider_name("gemini-2.0-flash") == "google"

    def test_gemini_case_insensitive(self) -> None:
        assert _infer_provider_name("Gemini-Pro") == "google"

    def test_llama_prefix_returns_ollama(self) -> None:
        assert _infer_provider_name("llama3.2:latest") == "ollama"

    def test_llama_case_insensitive(self) -> None:
        assert _infer_provider_name("Llama-3.1-70B") == "ollama"

    def test_unknown_prefix_returns_openai(self) -> None:
        assert _infer_provider_name("gpt-5.2") == "openai"

    def test_empty_string_returns_openai(self) -> None:
        assert _infer_provider_name("") == "openai"

    def test_numeric_prefix_returns_openai(self) -> None:
        assert _infer_provider_name("4o-mini") == "openai"

    # -- Ollama open-source model families (v362) --

    def test_mistral_prefix_returns_ollama(self) -> None:
        assert _infer_provider_name("mistral-7b") == "ollama"

    def test_mistral_case_insensitive(self) -> None:
        assert _infer_provider_name("Mistral-Large") == "ollama"

    def test_mixtral_prefix_returns_ollama(self) -> None:
        assert _infer_provider_name("mixtral-8x7b") == "ollama"

    def test_phi_prefix_returns_ollama(self) -> None:
        assert _infer_provider_name("phi-3") == "ollama"

    def test_codellama_prefix_returns_ollama(self) -> None:
        assert _infer_provider_name("codellama:13b") == "ollama"

    def test_deepseek_prefix_returns_ollama(self) -> None:
        assert _infer_provider_name("deepseek-coder-v2") == "ollama"

    def test_qwen_prefix_returns_ollama(self) -> None:
        assert _infer_provider_name("qwen2.5:72b") == "ollama"

    def test_starcoder_prefix_returns_ollama(self) -> None:
        assert _infer_provider_name("starcoder2:15b") == "ollama"

    def test_vicuna_prefix_returns_ollama(self) -> None:
        assert _infer_provider_name("vicuna:13b") == "ollama"

    def test_yi_prefix_returns_ollama(self) -> None:
        assert _infer_provider_name("yi:34b") == "ollama"

    # -- OpenAI reasoning model prefixes (v362) --

    def test_o1_prefix_returns_openai(self) -> None:
        assert _infer_provider_name("o1-preview") == "openai"

    def test_o3_prefix_returns_openai(self) -> None:
        assert _infer_provider_name("o3-mini") == "openai"

    def test_o4_prefix_returns_openai(self) -> None:
        assert _infer_provider_name("o4-mini") == "openai"

    def test_gpt_prefix_returns_openai(self) -> None:
        assert _infer_provider_name("gpt-4o") == "openai"


class TestModelPrefixConstants:
    """Verify the prefix tuple constants are well-formed."""

    def test_ollama_prefixes_are_lowercase(self) -> None:
        for prefix in _OLLAMA_MODEL_PREFIXES:
            assert prefix == prefix.lower(), f"{prefix!r} should be lowercase"

    def test_openai_prefixes_are_lowercase(self) -> None:
        for prefix in _OPENAI_MODEL_PREFIXES:
            assert prefix == prefix.lower(), f"{prefix!r} should be lowercase"

    def test_ollama_prefixes_non_empty(self) -> None:
        assert len(_OLLAMA_MODEL_PREFIXES) >= 5

    def test_openai_prefixes_non_empty(self) -> None:
        assert len(_OPENAI_MODEL_PREFIXES) >= 2


# ---------------------------------------------------------------------------
# HandModel dataclass
# ---------------------------------------------------------------------------


class TestHandModel:
    def test_frozen(self) -> None:
        hm = resolve_hand_model("gpt-5.2")
        with pytest.raises(AttributeError):
            hm.model = "other"  # type: ignore[misc]

    def test_raw_preserves_original_input(self) -> None:
        hm = resolve_hand_model("anthropic/claude-3-5-sonnet-latest")
        assert hm.raw == "anthropic/claude-3-5-sonnet-latest"


# ---------------------------------------------------------------------------
# resolve_hand_model
# ---------------------------------------------------------------------------


def test_resolve_hand_model_default_uses_ollama_default() -> None:
    hand_model = resolve_hand_model("default")
    assert hand_model.provider.name == "ollama"
    assert hand_model.model == "llama3.2:latest"


def test_resolve_hand_model_explicit_provider_prefix() -> None:
    hand_model = resolve_hand_model("anthropic/claude-3-5-sonnet-latest")
    assert hand_model.provider.name == "anthropic"
    assert hand_model.model == "claude-3-5-sonnet-latest"


def test_resolve_hand_model_infers_anthropic_from_bare_model() -> None:
    hand_model = resolve_hand_model("claude-3-5-sonnet-latest")
    assert hand_model.provider.name == "anthropic"
    assert hand_model.model == "claude-3-5-sonnet-latest"


def test_resolve_hand_model_infers_google_from_bare_model() -> None:
    hand_model = resolve_hand_model("gemini-2.0-flash")
    assert hand_model.provider.name == "google"
    assert hand_model.model == "gemini-2.0-flash"


def test_resolve_hand_model_infers_ollama_from_bare_model() -> None:
    hand_model = resolve_hand_model("llama3.2:latest")
    assert hand_model.provider.name == "ollama"
    assert hand_model.model == "llama3.2:latest"


def test_resolve_hand_model_explicit_ollama_uses_provider_default_model() -> None:
    hand_model = resolve_hand_model("ollama/")
    assert hand_model.provider.name == "ollama"
    assert hand_model.model == "llama3.2:latest"


def test_resolve_hand_model_provider_name_uses_provider_default_model() -> None:
    hand_model = resolve_hand_model("ollama")
    assert hand_model.provider.name == "ollama"
    assert hand_model.model == "llama3.2:latest"


def test_resolve_hand_model_falls_back_to_openai_for_unknown_prefix() -> None:
    hand_model = resolve_hand_model("gpt-5.2")
    assert hand_model.provider.name == "openai"
    assert hand_model.model == "gpt-5.2"


def test_resolve_hand_model_unrecognized_provider_slash_falls_through() -> None:
    """When provider/model format has an unrecognized provider prefix,
    the slash path falls through and _infer_provider_name handles it."""
    hand_model = resolve_hand_model("customllm/my-model")
    # "customllm" is not in PROVIDERS, so falls to _infer_provider_name
    # which defaults to openai for unrecognized prefixes
    assert hand_model.provider.name == "openai"
    assert hand_model.model == "customllm/my-model"
    assert hand_model.raw == "customllm/my-model"


def test_resolve_hand_model_infers_ollama_from_mistral() -> None:
    hand_model = resolve_hand_model("mistral-7b")
    assert hand_model.provider.name == "ollama"
    assert hand_model.model == "mistral-7b"


def test_resolve_hand_model_infers_ollama_from_deepseek() -> None:
    hand_model = resolve_hand_model("deepseek-coder-v2")
    assert hand_model.provider.name == "ollama"
    assert hand_model.model == "deepseek-coder-v2"


def test_resolve_hand_model_infers_openai_from_o1() -> None:
    hand_model = resolve_hand_model("o1-preview")
    assert hand_model.provider.name == "openai"
    assert hand_model.model == "o1-preview"


def test_resolve_hand_model_none_uses_default() -> None:
    hand_model = resolve_hand_model(None)
    assert hand_model.provider.name == "ollama"
    assert hand_model.raw == "default"


def test_resolve_hand_model_empty_string_uses_default() -> None:
    hand_model = resolve_hand_model("")
    assert hand_model.provider.name == "ollama"
    assert hand_model.raw == "default"


def test_resolve_hand_model_whitespace_only_uses_default() -> None:
    hand_model = resolve_hand_model("   ")
    assert hand_model.provider.name == "ollama"
    assert hand_model.raw == "default"


# ---------------------------------------------------------------------------
# Helper: build a HandModel with a fake provider
# ---------------------------------------------------------------------------


def _fake_hand_model(provider_name: str, model: str = "test-model") -> HandModel:
    provider = SimpleNamespace(name=provider_name, inner=MagicMock())
    return HandModel(provider=provider, model=model, raw=model)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# build_langchain_chat_model
# ---------------------------------------------------------------------------


class TestBuildLangchainChatModelOpenAI:
    @patch(
        "helping_hands.lib.hands.v1.hand.model_provider.ChatOpenAI",
        create=True,
    )
    def test_openai_returns_chat_openai(self, mock_cls: MagicMock) -> None:
        # We patch the lazy import by inserting a mock into the module namespace
        sentinel = object()
        mock_cls.return_value = sentinel
        hm = _fake_hand_model("openai", "gpt-5.2")
        with patch.dict(
            "sys.modules",
            {"langchain_openai": SimpleNamespace(ChatOpenAI=mock_cls)},
        ):
            result = build_langchain_chat_model(hm, streaming=True)
        mock_cls.assert_called_once_with(model_name="gpt-5.2", streaming=True)
        assert result is sentinel


class TestBuildLangchainChatModelOllama:
    def test_ollama_uses_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:1234/v1")
        monkeypatch.setenv("OLLAMA_API_KEY", "secret")
        mock_cls = MagicMock()
        hm = _fake_hand_model("ollama", "llama3.2:latest")
        with patch.dict(
            "sys.modules",
            {"langchain_openai": SimpleNamespace(ChatOpenAI=mock_cls)},
        ):
            build_langchain_chat_model(hm, streaming=False)
        mock_cls.assert_called_once_with(
            model_name="llama3.2:latest",
            streaming=False,
            base_url="http://custom:1234/v1",
            api_key="secret",
        )

    def test_ollama_defaults_without_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
        mock_cls = MagicMock()
        hm = _fake_hand_model("ollama", "llama3.2:latest")
        with patch.dict(
            "sys.modules",
            {"langchain_openai": SimpleNamespace(ChatOpenAI=mock_cls)},
        ):
            build_langchain_chat_model(hm, streaming=True)
        _, kwargs = mock_cls.call_args
        assert kwargs["base_url"] == "http://localhost:11434/v1"
        assert kwargs["api_key"] == "ollama"


class TestBuildLangchainChatModelAnthropic:
    def test_anthropic_returns_chat_anthropic(self) -> None:
        mock_cls = MagicMock()
        sentinel = object()
        mock_cls.return_value = sentinel
        hm = _fake_hand_model("anthropic", "claude-sonnet-4-5")
        with patch.dict(
            "sys.modules",
            {"langchain_anthropic": SimpleNamespace(ChatAnthropic=mock_cls)},
        ):
            result = build_langchain_chat_model(hm, streaming=True)
        mock_cls.assert_called_once_with(model="claude-sonnet-4-5", streaming=True)
        assert result is sentinel

    def test_anthropic_import_error(self) -> None:
        hm = _fake_hand_model("anthropic")
        with (
            patch.dict("sys.modules", {"langchain_anthropic": None}),
            pytest.raises(RuntimeError, match="langchain-anthropic"),
        ):
            build_langchain_chat_model(hm, streaming=False)


class TestBuildLangchainChatModelGoogle:
    def test_google_returns_chat_google(self) -> None:
        mock_cls = MagicMock()
        sentinel = object()
        mock_cls.return_value = sentinel
        hm = _fake_hand_model("google", "gemini-2.0-flash")
        with patch.dict(
            "sys.modules",
            {
                "langchain_google_genai": SimpleNamespace(
                    ChatGoogleGenerativeAI=mock_cls
                )
            },
        ):
            result = build_langchain_chat_model(hm, streaming=False)
        mock_cls.assert_called_once_with(model="gemini-2.0-flash", streaming=False)
        assert result is sentinel

    def test_google_import_error(self) -> None:
        hm = _fake_hand_model("google")
        with (
            patch.dict("sys.modules", {"langchain_google_genai": None}),
            pytest.raises(RuntimeError, match="langchain-google-genai"),
        ):
            build_langchain_chat_model(hm, streaming=False)


class TestBuildLangchainChatModelLiteLLM:
    def test_litellm_returns_chat_litellm(self) -> None:
        mock_cls = MagicMock()
        sentinel = object()
        mock_cls.return_value = sentinel
        hm = _fake_hand_model("litellm", "gpt-5.2")
        chat_models = SimpleNamespace(ChatLiteLLM=mock_cls)
        with patch.dict(
            "sys.modules",
            {
                "langchain_community": MagicMock(),
                "langchain_community.chat_models": chat_models,
            },
        ):
            result = build_langchain_chat_model(hm, streaming=True)
        mock_cls.assert_called_once_with(model="gpt-5.2", streaming=True)
        assert result is sentinel

    def test_litellm_import_error(self) -> None:
        hm = _fake_hand_model("litellm")
        with (
            patch.dict(
                "sys.modules",
                {"langchain_community": None, "langchain_community.chat_models": None},
            ),
            pytest.raises(RuntimeError, match="langchain-community"),
        ):
            build_langchain_chat_model(hm, streaming=False)


class TestBuildLangchainChatModelUnsupported:
    def test_unsupported_provider_raises(self) -> None:
        hm = _fake_hand_model("unknown-provider")
        with pytest.raises(RuntimeError, match="unsupported provider"):
            build_langchain_chat_model(hm, streaming=False)


# ---------------------------------------------------------------------------
# build_atomic_client
# ---------------------------------------------------------------------------


class TestBuildAtomicClientOpenAI:
    def test_openai_calls_instructor_from_openai(self) -> None:
        mock_instructor = MagicMock()
        sentinel = object()
        mock_instructor.from_openai.return_value = sentinel
        hm = _fake_hand_model("openai")
        with patch.dict("sys.modules", {"instructor": mock_instructor}):
            result = build_atomic_client(hm)
        mock_instructor.from_openai.assert_called_once_with(hm.provider.inner)
        assert result is sentinel


class TestBuildAtomicClientLiteLLM:
    def test_litellm_calls_instructor_from_litellm(self) -> None:
        mock_instructor = MagicMock()
        mock_instructor.from_litellm = MagicMock()
        sentinel = object()
        mock_instructor.from_litellm.return_value = sentinel
        hm = _fake_hand_model("litellm")
        hm.provider.inner.completion = MagicMock()
        with patch.dict("sys.modules", {"instructor": mock_instructor}):
            result = build_atomic_client(hm)
        mock_instructor.from_litellm.assert_called_once_with(
            hm.provider.inner.completion
        )
        assert result is sentinel

    def test_litellm_raises_when_instructor_lacks_from_litellm(self) -> None:
        mock_instructor = MagicMock(spec=[])  # no from_litellm attribute
        hm = _fake_hand_model("litellm")
        with (
            patch.dict("sys.modules", {"instructor": mock_instructor}),
            pytest.raises(RuntimeError, match="not supported by this instructor"),
        ):
            build_atomic_client(hm)


class TestBuildAtomicClientUnsupported:
    def test_unsupported_provider_raises(self) -> None:
        mock_instructor = MagicMock()
        hm = _fake_hand_model("anthropic")
        with (
            patch.dict("sys.modules", {"instructor": mock_instructor}),
            pytest.raises(RuntimeError, match="not supported by atomic"),
        ):
            build_atomic_client(hm)


# ---------------------------------------------------------------------------
# _require_langchain_class — direct unit tests
# ---------------------------------------------------------------------------


class TestRequireLangchainClass:
    """Direct tests for the lazy-import helper."""

    def test_success_returns_class(self) -> None:
        """Successful import returns the requested class attribute."""
        mock_cls = type("FakeChat", (), {})
        mock_mod = SimpleNamespace(FakeChat=mock_cls)
        with patch.dict("sys.modules", {"fake_langchain_mod": mock_mod}):
            result = _require_langchain_class(
                "fake_langchain_mod", "FakeChat", hint="test"
            )
        assert result is mock_cls

    def test_failure_derives_install_from_module_path(self) -> None:
        """When *install* is None, the pip package is derived from module_path."""
        with (
            patch.dict("sys.modules", {"langchain_custom": None}),
            pytest.raises(RuntimeError, match="uv add langchain-custom"),
        ):
            _require_langchain_class(
                "langchain_custom", "Chat", hint="custom models require it"
            )

    def test_failure_uses_explicit_install_string(self) -> None:
        """When *install* is provided, it appears in the error message."""
        with (
            patch.dict("sys.modules", {"langchain_community.chat_models": None}),
            pytest.raises(RuntimeError, match="uv add my-pkg extra-pkg"),
        ):
            _require_langchain_class(
                "langchain_community.chat_models",
                "ChatFoo",
                hint="need custom install",
                install="my-pkg extra-pkg",
            )


# ---------------------------------------------------------------------------
# resolve_hand_model — additional provider-name branches
# ---------------------------------------------------------------------------


class TestResolveHandModelDirectProviderNames:
    """When the raw input exactly matches a known provider name, the provider's
    default model should be returned without going through inference."""

    def test_openai_provider_name(self) -> None:
        hm = resolve_hand_model("openai")
        assert hm.provider.name == "openai"
        assert hm.model == hm.provider.default_model
        assert hm.raw == "openai"

    def test_anthropic_provider_name(self) -> None:
        hm = resolve_hand_model("anthropic")
        assert hm.provider.name == "anthropic"
        assert hm.model == hm.provider.default_model
        assert hm.raw == "anthropic"

    def test_google_provider_name(self) -> None:
        hm = resolve_hand_model("google")
        assert hm.provider.name == "google"
        assert hm.model == hm.provider.default_model
        assert hm.raw == "google"

    def test_litellm_provider_name(self) -> None:
        hm = resolve_hand_model("litellm")
        assert hm.provider.name == "litellm"
        assert hm.model == hm.provider.default_model
        assert hm.raw == "litellm"


class TestResolveHandModelProviderSlashEmpty:
    """When input is 'provider/' (trailing slash, empty model), the provider's
    default model should be used."""

    def test_openai_trailing_slash(self) -> None:
        hm = resolve_hand_model("openai/")
        assert hm.provider.name == "openai"
        assert hm.model == hm.provider.default_model

    def test_anthropic_trailing_slash(self) -> None:
        hm = resolve_hand_model("anthropic/")
        assert hm.provider.name == "anthropic"
        assert hm.model == hm.provider.default_model

    def test_google_trailing_slash(self) -> None:
        hm = resolve_hand_model("google/")
        assert hm.provider.name == "google"
        assert hm.model == hm.provider.default_model

    def test_litellm_trailing_slash(self) -> None:
        hm = resolve_hand_model("litellm/")
        assert hm.provider.name == "litellm"
        assert hm.model == hm.provider.default_model

    def test_provider_slash_whitespace_model(self) -> None:
        """'provider/  ' should strip to empty and use the default model."""
        hm = resolve_hand_model("openai/  ")
        assert hm.provider.name == "openai"
        assert hm.model == hm.provider.default_model


# ---------------------------------------------------------------------------
# build_langchain_chat_model / build_atomic_client — empty model validation
# ---------------------------------------------------------------------------


class TestBuildEmptyModelValidation:
    """Both build functions call require_non_empty_string on the model name."""

    def test_langchain_empty_model_raises(self) -> None:
        hm = _fake_hand_model("openai", "")
        with pytest.raises(ValueError, match=r"hand_model\.model"):
            build_langchain_chat_model(hm, streaming=False)

    def test_atomic_empty_model_raises(self) -> None:
        mock_instructor = MagicMock()
        hm = _fake_hand_model("openai", "")
        with (
            patch.dict("sys.modules", {"instructor": mock_instructor}),
            pytest.raises(ValueError, match=r"hand_model\.model"),
        ):
            build_atomic_client(hm)
