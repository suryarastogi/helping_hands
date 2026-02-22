from helping_hands.lib.hands.v1.hand.model_provider import resolve_hand_model


def test_resolve_hand_model_default_uses_openai_default() -> None:
    hand_model = resolve_hand_model("default")
    assert hand_model.provider.name == "openai"
    assert hand_model.model == "gpt-5.2"


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


def test_resolve_hand_model_falls_back_to_openai_for_unknown_prefix() -> None:
    hand_model = resolve_hand_model("gpt-5.2")
    assert hand_model.provider.name == "openai"
    assert hand_model.model == "gpt-5.2"
