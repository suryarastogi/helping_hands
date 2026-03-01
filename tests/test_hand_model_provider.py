import pytest

from helping_hands.lib.hands.v1.hand.model_provider import (
    HandModel,
    resolve_hand_model,
)

# --- HandModel dataclass ---


def test_hand_model_attributes() -> None:
    hand_model = resolve_hand_model("openai/gpt-5.2")
    assert isinstance(hand_model, HandModel)
    assert hand_model.provider.name == "openai"
    assert hand_model.model == "gpt-5.2"
    assert hand_model.raw == "openai/gpt-5.2"


def test_hand_model_is_frozen() -> None:
    hand_model = resolve_hand_model("gpt-5.2")
    with pytest.raises(AttributeError):
        hand_model.model = "other"  # type: ignore[misc]


# --- resolve_hand_model ---


def test_resolve_hand_model_empty_string_uses_default() -> None:
    hand_model = resolve_hand_model("")
    assert hand_model.provider.name == "ollama"
    assert hand_model.model == "llama3.2:latest"
    assert hand_model.raw == "default"


def test_resolve_hand_model_none_uses_default() -> None:
    hand_model = resolve_hand_model(None)
    assert hand_model.provider.name == "ollama"
    assert hand_model.model == "llama3.2:latest"


def test_resolve_hand_model_litellm_provider_prefix() -> None:
    hand_model = resolve_hand_model("litellm/gpt-4o")
    assert hand_model.provider.name == "litellm"
    assert hand_model.model == "gpt-4o"


def test_resolve_hand_model_explicit_openai_prefix() -> None:
    hand_model = resolve_hand_model("openai/gpt-5.2")
    assert hand_model.provider.name == "openai"
    assert hand_model.model == "gpt-5.2"


def test_resolve_hand_model_whitespace_stripped() -> None:
    hand_model = resolve_hand_model("  gpt-5.2  ")
    assert hand_model.provider.name == "openai"
    assert hand_model.model == "gpt-5.2"


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
