"""Tests for GooseCLIHand static helper methods."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand
from helping_hands.lib.repo import RepoIndex


def _make_goose_hand(tmp_path: Path, **config_kwargs) -> GooseCLIHand:
    """Build a GooseCLIHand with subprocess execution mocked out."""
    (tmp_path / "main.py").write_text("")
    repo_index = RepoIndex.from_path(tmp_path)
    defaults = {"repo": str(tmp_path), "model": "anthropic/claude-test"}
    defaults.update(config_kwargs)
    config = Config(**defaults)
    with patch.object(GooseCLIHand, "__init__", lambda self, *a, **kw: None):
        hand = GooseCLIHand(config, repo_index)
    hand.config = config
    return hand


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


# ---------------------------------------------------------------------------
# _describe_auth
# ---------------------------------------------------------------------------


class TestDescribeAuth:
    def test_anthropic_key_set(self, tmp_path, monkeypatch) -> None:
        hand = _make_goose_hand(tmp_path, model="anthropic/claude-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        result = hand._describe_auth()
        assert "anthropic" in result
        assert "ANTHROPIC_API_KEY" in result
        assert "set" in result
        assert "not set" not in result

    def test_anthropic_key_not_set(self, tmp_path, monkeypatch) -> None:
        hand = _make_goose_hand(tmp_path, model="anthropic/claude-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = hand._describe_auth()
        assert "not set" in result

    def test_openai_provider(self, tmp_path, monkeypatch) -> None:
        hand = _make_goose_hand(tmp_path, model="openai/gpt-5.2")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        result = hand._describe_auth()
        assert "openai" in result
        assert "OPENAI_API_KEY" in result

    def test_ollama_provider(self, tmp_path, monkeypatch) -> None:
        hand = _make_goose_hand(tmp_path, model="ollama/llama3.2")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        result = hand._describe_auth()
        assert "ollama" in result
        assert "OLLAMA_HOST" in result

    def test_unknown_provider_uses_provider_as_env_var(
        self, tmp_path, monkeypatch
    ) -> None:
        hand = _make_goose_hand(tmp_path, model="custom/model")
        monkeypatch.delenv("custom", raising=False)
        result = hand._describe_auth()
        assert "not set" in result


# ---------------------------------------------------------------------------
# _normalize_base_command
# ---------------------------------------------------------------------------


class TestNormalizeBaseCommand:
    def test_bare_goose(self) -> None:
        hand = GooseCLIHand.__new__(GooseCLIHand)
        result = hand._normalize_base_command(["goose"])
        assert result == ["goose", "run", "--with-builtin", "developer", "--text"]

    def test_goose_run(self) -> None:
        hand = GooseCLIHand.__new__(GooseCLIHand)
        result = hand._normalize_base_command(["goose", "run"])
        assert result == ["goose", "run", "--with-builtin", "developer", "--text"]

    def test_goose_run_instructions_compat(self) -> None:
        hand = GooseCLIHand.__new__(GooseCLIHand)
        result = hand._normalize_base_command(["goose", "run", "--instructions"])
        assert result == ["goose", "run", "--with-builtin", "developer", "--text"]

    def test_passthrough_custom_command(self) -> None:
        hand = GooseCLIHand.__new__(GooseCLIHand)
        custom = ["goose", "run", "--custom-flag", "value"]
        result = hand._normalize_base_command(custom)
        assert result == custom


# ---------------------------------------------------------------------------
# _pr_description_cmd
# ---------------------------------------------------------------------------


class TestPrDescriptionCmd:
    def test_anthropic_with_claude_binary(self, tmp_path) -> None:
        hand = _make_goose_hand(tmp_path, model="anthropic/claude-test")
        with patch("shutil.which", return_value="/usr/bin/claude"):
            result = hand._pr_description_cmd()
        assert result == ["claude", "-p", "--output-format", "text"]

    def test_anthropic_without_claude_binary(self, tmp_path) -> None:
        hand = _make_goose_hand(tmp_path, model="anthropic/claude-test")
        with patch("shutil.which", return_value=None):
            result = hand._pr_description_cmd()
        assert result is None

    def test_non_anthropic_returns_none(self, tmp_path) -> None:
        hand = _make_goose_hand(tmp_path, model="openai/gpt-5.2")
        result = hand._pr_description_cmd()
        assert result is None


# ---------------------------------------------------------------------------
# _has_goose_builtin_flag
# ---------------------------------------------------------------------------


class TestHasGooseBuiltinFlag:
    def test_detects_flag(self) -> None:
        assert GooseCLIHand._has_goose_builtin_flag(
            ["goose", "run", "--with-builtin", "developer"]
        )

    def test_detects_equals_form(self) -> None:
        assert GooseCLIHand._has_goose_builtin_flag(
            ["goose", "run", "--with-builtin=developer"]
        )

    def test_missing_flag(self) -> None:
        assert not GooseCLIHand._has_goose_builtin_flag(["goose", "run", "--text"])


# ---------------------------------------------------------------------------
# _apply_backend_defaults
# ---------------------------------------------------------------------------


class TestApplyBackendDefaults:
    def test_adds_builtin_flag(self) -> None:
        hand = GooseCLIHand.__new__(GooseCLIHand)
        result = hand._apply_backend_defaults(["goose", "run", "--text", "prompt"])
        assert "--with-builtin" in result
        assert "developer" in result

    def test_skips_if_builtin_present(self) -> None:
        hand = GooseCLIHand.__new__(GooseCLIHand)
        cmd = ["goose", "run", "--with-builtin", "dev", "--text"]
        result = hand._apply_backend_defaults(cmd)
        assert result == cmd

    def test_skips_if_not_goose_run(self) -> None:
        hand = GooseCLIHand.__new__(GooseCLIHand)
        cmd = ["some-other-cmd"]
        result = hand._apply_backend_defaults(cmd)
        assert result == cmd


# ---------------------------------------------------------------------------
# _resolve_ollama_host
# ---------------------------------------------------------------------------


class TestResolveOllamaHost:
    def test_explicit_host(self) -> None:
        env = {"OLLAMA_HOST": "http://custom:11434"}
        assert GooseCLIHand._resolve_ollama_host(env) == "http://custom:11434"

    def test_fallback_to_base_url(self) -> None:
        env = {"OLLAMA_BASE_URL": "http://alt:11434"}
        assert GooseCLIHand._resolve_ollama_host(env) == "http://alt:11434"

    def test_default_localhost(self) -> None:
        assert GooseCLIHand._resolve_ollama_host({}) == "http://localhost:11434"

    def test_host_takes_precedence_over_base_url(self) -> None:
        env = {
            "OLLAMA_HOST": "http://primary:11434",
            "OLLAMA_BASE_URL": "http://secondary:11434",
        }
        assert GooseCLIHand._resolve_ollama_host(env) == "http://primary:11434"
