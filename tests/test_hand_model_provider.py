import pytest

from helping_hands.lib.hands.v1.hand.model_provider import (
    _infer_provider_name,
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
