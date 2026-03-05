"""Tests for GooseCLIHand static helper methods."""

from __future__ import annotations

from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand


class TestNormalizeGooseProvider:
    def test_gemini_maps_to_google(self) -> None:
        assert GooseCLIHand._normalize_goose_provider("gemini") == "google"

    def test_case_insensitive(self) -> None:
        assert GooseCLIHand._normalize_goose_provider("GEMINI") == "google"
        assert GooseCLIHand._normalize_goose_provider("Anthropic") == "anthropic"

    def test_passthrough_known_providers(self) -> None:
        assert GooseCLIHand._normalize_goose_provider("openai") == "openai"
        assert GooseCLIHand._normalize_goose_provider("ollama") == "ollama"

    def test_empty_string_returns_empty(self) -> None:
        assert GooseCLIHand._normalize_goose_provider("") == ""

    def test_whitespace_only_returns_empty(self) -> None:
        assert GooseCLIHand._normalize_goose_provider("   ") == ""


class TestInferGooseProviderFromModel:
    def test_claude_prefix(self) -> None:
        assert (
            GooseCLIHand._infer_goose_provider_from_model("claude-opus") == "anthropic"
        )

    def test_anthropic_slash_prefix(self) -> None:
        assert (
            GooseCLIHand._infer_goose_provider_from_model("anthropic/claude-3.5")
            == "anthropic"
        )

    def test_gemini_prefix(self) -> None:
        assert GooseCLIHand._infer_goose_provider_from_model("gemini-2.0") == "google"

    def test_google_slash_prefix(self) -> None:
        assert (
            GooseCLIHand._infer_goose_provider_from_model("google/gemini-pro")
            == "google"
        )

    def test_llama_prefix(self) -> None:
        assert GooseCLIHand._infer_goose_provider_from_model("llama3.2") == "ollama"

    def test_ollama_slash_prefix(self) -> None:
        assert GooseCLIHand._infer_goose_provider_from_model("ollama/phi3") == "ollama"

    def test_defaults_to_openai(self) -> None:
        assert GooseCLIHand._infer_goose_provider_from_model("gpt-5.2") == "openai"

    def test_unknown_model_defaults_openai(self) -> None:
        assert GooseCLIHand._infer_goose_provider_from_model("some-custom") == "openai"


class TestNormalizeOllamaHost:
    def test_adds_http_scheme_when_missing(self) -> None:
        assert (
            GooseCLIHand._normalize_ollama_host("localhost:11434")
            == "http://localhost:11434"
        )

    def test_preserves_http(self) -> None:
        assert (
            GooseCLIHand._normalize_ollama_host("http://myhost:11434")
            == "http://myhost:11434"
        )

    def test_preserves_https(self) -> None:
        assert (
            GooseCLIHand._normalize_ollama_host("https://secure.host")
            == "https://secure.host"
        )

    def test_rejects_ftp_scheme(self) -> None:
        assert GooseCLIHand._normalize_ollama_host("ftp://host") == ""

    def test_empty_string(self) -> None:
        assert GooseCLIHand._normalize_ollama_host("") == ""

    def test_whitespace_only(self) -> None:
        assert GooseCLIHand._normalize_ollama_host("   ") == ""

    def test_strips_path_to_netloc_only(self) -> None:
        assert (
            GooseCLIHand._normalize_ollama_host("http://host:11434/some/path")
            == "http://host:11434"
        )
