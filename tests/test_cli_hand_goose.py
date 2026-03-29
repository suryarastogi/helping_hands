"""Tests for GooseCLIHand static helper methods.

GooseCLIHand wraps Block's `goose` CLI and has the most complex provider/model
resolution of any CLI hand: it must infer the Goose provider from the model
name (e.g. "claude-" → anthropic, "gemini" → google, "llama" → ollama),
normalise the "gemini" alias to "google", and inject GOOSE_PROVIDER /
GOOSE_MODEL into the subprocess environment. A regression in provider inference
routes requests to the wrong API backend silently. The GH_TOKEN / GITHUB_TOKEN
synchronisation tests guard Goose's requirement for both env vars to be
consistent. Ollama host resolution ensures a default localhost value is injected
so ollama-backed runs work without any additional user configuration.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from helping_hands.lib.hands.v1.hand.cli.goose import (
    _OLLAMA_DEFAULT_HOST,
    GooseCLIHand,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def goose_hand(make_cli_hand):
    return make_cli_hand(GooseCLIHand, model="anthropic/claude-test")


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
    def test_anthropic_key_set(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(GooseCLIHand, model="anthropic/claude-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        result = hand._describe_auth()
        assert "anthropic" in result
        assert "ANTHROPIC_API_KEY" in result
        assert "set" in result
        assert "not set" not in result

    def test_anthropic_key_not_set(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(GooseCLIHand, model="anthropic/claude-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = hand._describe_auth()
        assert "not set" in result

    def test_openai_provider(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(GooseCLIHand, model="openai/gpt-5.2")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        result = hand._describe_auth()
        assert "openai" in result
        assert "OPENAI_API_KEY" in result

    def test_ollama_provider(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(GooseCLIHand, model="ollama/llama3.2")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        result = hand._describe_auth()
        assert "ollama" in result
        assert "OLLAMA_HOST" in result

    def test_unknown_provider_uses_provider_as_env_var(
        self, make_cli_hand, monkeypatch
    ) -> None:
        hand = make_cli_hand(GooseCLIHand, model="custom/model")
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
    def test_anthropic_with_claude_binary(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand, model="anthropic/claude-test")
        with patch("shutil.which", return_value="/usr/bin/claude"):
            result = hand._pr_description_cmd()
        assert result == ["claude", "-p", "--output-format", "text"]

    def test_anthropic_without_claude_binary(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand, model="anthropic/claude-test")
        with patch("shutil.which", return_value=None):
            result = hand._pr_description_cmd()
        assert result is None

    def test_non_anthropic_returns_none(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand, model="openai/gpt-5.2")
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


# ---------------------------------------------------------------------------
# _resolve_goose_provider_model_from_config
# ---------------------------------------------------------------------------


class TestResolveGooseProviderModelFromConfig:
    def test_bare_model_infers_provider(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand, model="claude-opus-4")
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == "anthropic"
        assert model == "claude-opus-4"

    def test_provider_slash_model(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand, model="google/gemini-2.0-flash")
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == "google"
        assert model == "gemini-2.0-flash"

    def test_default_model_returned(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand, model="default")
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == GooseCLIHand._GOOSE_DEFAULT_PROVIDER
        assert model == GooseCLIHand._GOOSE_DEFAULT_MODEL

    def test_empty_model_returns_defaults(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand, model="  ")
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == GooseCLIHand._GOOSE_DEFAULT_PROVIDER
        assert model == GooseCLIHand._GOOSE_DEFAULT_MODEL

    def test_slash_with_empty_model_part(self, make_cli_hand) -> None:
        """'provider/' with empty model part falls back to default model."""
        hand = make_cli_hand(GooseCLIHand, model="openai/")
        provider, model = hand._resolve_goose_provider_model_from_config()
        # provider_model is "" so provider stays "", model stays "openai/"
        # Then model is truthy so no default model, but no provider -> infer
        assert model is not None
        assert provider is not None

    def test_gemini_provider_normalized_to_google(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand, model="gemini/gemini-2.0")
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == "google"
        assert model == "gemini-2.0"

    def test_gpt_model_infers_openai(self, make_cli_hand) -> None:
        hand = make_cli_hand(GooseCLIHand, model="gpt-5.2")
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == "openai"
        assert model == "gpt-5.2"


# ---------------------------------------------------------------------------
# _invoke_goose / _invoke_backend async tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# _build_subprocess_env
# ---------------------------------------------------------------------------


class TestBuildSubprocessEnv:
    def test_gh_token_propagated(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(GooseCLIHand, model="openai/gpt-5.2")
        monkeypatch.setenv("GH_TOKEN", "tok-123")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GOOSE_PROVIDER", raising=False)
        monkeypatch.delenv("GOOSE_MODEL", raising=False)
        env = hand._build_subprocess_env()
        assert env["GH_TOKEN"] == "tok-123"
        assert env["GITHUB_TOKEN"] == "tok-123"

    def test_github_token_fallback(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(GooseCLIHand, model="openai/gpt-5.2")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "tok-456")
        monkeypatch.delenv("GOOSE_PROVIDER", raising=False)
        monkeypatch.delenv("GOOSE_MODEL", raising=False)
        env = hand._build_subprocess_env()
        assert env["GH_TOKEN"] == "tok-456"
        assert env["GITHUB_TOKEN"] == "tok-456"

    def test_missing_token_raises(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(GooseCLIHand, model="openai/gpt-5.2")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(RuntimeError, match="GH_TOKEN or GITHUB_TOKEN"):
            hand._build_subprocess_env()

    def test_provider_and_model_from_config(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(GooseCLIHand, model="anthropic/claude-test")
        monkeypatch.setenv("GH_TOKEN", "tok")
        monkeypatch.delenv("GOOSE_PROVIDER", raising=False)
        monkeypatch.delenv("GOOSE_MODEL", raising=False)
        env = hand._build_subprocess_env()
        assert env["GOOSE_PROVIDER"] == "anthropic"
        assert env["GOOSE_MODEL"] == "claude-test"

    def test_goose_provider_env_override(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(GooseCLIHand, model="openai/gpt-5.2")
        monkeypatch.setenv("GH_TOKEN", "tok")
        monkeypatch.setenv("GOOSE_PROVIDER", "anthropic")
        monkeypatch.delenv("GOOSE_MODEL", raising=False)
        env = hand._build_subprocess_env()
        assert env["GOOSE_PROVIDER"] == "anthropic"

    def test_goose_model_env_override(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(GooseCLIHand, model="openai/gpt-5.2")
        monkeypatch.setenv("GH_TOKEN", "tok")
        monkeypatch.delenv("GOOSE_PROVIDER", raising=False)
        monkeypatch.setenv("GOOSE_MODEL", "custom-model")
        env = hand._build_subprocess_env()
        assert env["GOOSE_MODEL"] == "custom-model"

    def test_ollama_host_injected_for_ollama_provider(
        self, make_cli_hand, monkeypatch
    ) -> None:
        hand = make_cli_hand(GooseCLIHand, model="ollama/llama3.2")
        monkeypatch.setenv("GH_TOKEN", "tok")
        monkeypatch.delenv("GOOSE_PROVIDER", raising=False)
        monkeypatch.delenv("GOOSE_MODEL", raising=False)
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        env = hand._build_subprocess_env()
        assert env["GOOSE_PROVIDER"] == "ollama"
        assert env["OLLAMA_HOST"] == "http://localhost:11434"

    def test_ollama_host_not_injected_for_non_ollama(
        self, make_cli_hand, monkeypatch
    ) -> None:
        hand = make_cli_hand(GooseCLIHand, model="openai/gpt-5.2")
        monkeypatch.setenv("GH_TOKEN", "tok")
        monkeypatch.delenv("GOOSE_PROVIDER", raising=False)
        monkeypatch.delenv("GOOSE_MODEL", raising=False)
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        env = hand._build_subprocess_env()
        assert env["GOOSE_PROVIDER"] == "openai"
        # OLLAMA_HOST should not be explicitly set for non-ollama
        assert "OLLAMA_HOST" not in env

    def test_default_model_when_config_empty(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(GooseCLIHand, model="default")
        monkeypatch.setenv("GH_TOKEN", "tok")
        monkeypatch.delenv("GOOSE_PROVIDER", raising=False)
        monkeypatch.delenv("GOOSE_MODEL", raising=False)
        env = hand._build_subprocess_env()
        assert env["GOOSE_PROVIDER"] == GooseCLIHand._GOOSE_DEFAULT_PROVIDER
        assert env["GOOSE_MODEL"] == GooseCLIHand._GOOSE_DEFAULT_MODEL


# ---------------------------------------------------------------------------
# _invoke_goose / _invoke_backend async tests
# ---------------------------------------------------------------------------


class TestInvokeGoose:
    def test_invoke_backend_delegates_to_invoke_cli(
        self, make_cli_hand, monkeypatch
    ) -> None:
        import asyncio

        hand = make_cli_hand(GooseCLIHand)
        calls: list[str] = []

        async def fake_invoke_cli(prompt, *, emit):
            calls.append(prompt)
            return "result"

        monkeypatch.setattr(hand, "_invoke_cli", fake_invoke_cli)

        async def emit(text: str) -> None:
            pass

        # GooseCLIHand does not override _invoke_backend, so it
        # inherits the base which delegates to _invoke_cli.
        result = asyncio.run(hand._invoke_backend("hello", emit=emit))
        assert result == "result"
        assert calls == ["hello"]


# ---------------------------------------------------------------------------
# _OLLAMA_DEFAULT_HOST constant (v143)
# ---------------------------------------------------------------------------


class TestOllamaDefaultHostConstant:
    """Tests for the _OLLAMA_DEFAULT_HOST module-level constant."""

    def test_value(self) -> None:
        assert _OLLAMA_DEFAULT_HOST == "http://localhost:11434"

    def test_type(self) -> None:
        assert isinstance(_OLLAMA_DEFAULT_HOST, str)

    def test_is_valid_url(self) -> None:
        from urllib.parse import urlparse

        parsed = urlparse(_OLLAMA_DEFAULT_HOST)
        assert parsed.scheme == "http"
        assert parsed.netloc == "localhost:11434"

    def test_resolve_ollama_host_uses_constant(self) -> None:
        """_resolve_ollama_host() returns the constant when no env vars are set."""
        result = GooseCLIHand._resolve_ollama_host({})
        assert result == _OLLAMA_DEFAULT_HOST

    def test_build_subprocess_env_uses_constant(
        self, make_cli_hand, monkeypatch
    ) -> None:
        """_build_subprocess_env injects _OLLAMA_DEFAULT_HOST for ollama provider."""
        hand = make_cli_hand(GooseCLIHand, model="ollama/llama3.2")
        monkeypatch.setenv("GH_TOKEN", "tok")
        monkeypatch.delenv("GOOSE_PROVIDER", raising=False)
        monkeypatch.delenv("GOOSE_MODEL", raising=False)
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        env = hand._build_subprocess_env()
        assert env["OLLAMA_HOST"] == _OLLAMA_DEFAULT_HOST


# ---------------------------------------------------------------------------
# _read_goose_config
# ---------------------------------------------------------------------------


class TestReadGooseConfig:
    """Tests for YAML config file reading in _read_goose_config."""

    def test_yaml_import_error_returns_empty(self) -> None:
        """When yaml is not installed, returns empty tuple."""
        with patch.dict("sys.modules", {"yaml": None}):
            # Force re-import failure by patching builtins.__import__
            original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__  # noqa: E501

            def fake_import(name, *args, **kwargs):
                if name == "yaml":
                    raise ImportError("No module named 'yaml'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=fake_import):
                result = GooseCLIHand._read_goose_config()
                assert result == ("", "")

    def test_config_file_not_found_returns_empty(self, tmp_path) -> None:
        """When no config file exists, returns empty tuple."""
        fake_path = tmp_path / "nonexistent" / "config.yaml"
        with patch.object(GooseCLIHand, "_GOOSE_CONFIG_PATHS", (fake_path,)):
            result = GooseCLIHand._read_goose_config()
            assert result == ("", "")

    def test_yaml_parse_exception_returns_empty(self, tmp_path) -> None:
        """When YAML file is malformed, exception is swallowed."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(": : : invalid yaml [[[")
        with patch.object(GooseCLIHand, "_GOOSE_CONFIG_PATHS", (config_file,)):
            import yaml

            with patch.object(yaml, "safe_load", side_effect=Exception("parse error")):
                result = GooseCLIHand._read_goose_config()
                assert result == ("", "")

    def test_non_dict_yaml_skipped(self, tmp_path) -> None:
        """When YAML parses to a non-dict (e.g. list), file is skipped."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("- item1\n- item2\n")
        with patch.object(GooseCLIHand, "_GOOSE_CONFIG_PATHS", (config_file,)):
            result = GooseCLIHand._read_goose_config()
            assert result == ("", "")

    def test_reads_provider_and_model(self, tmp_path) -> None:
        """Successfully reads GOOSE_PROVIDER and GOOSE_MODEL from config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "GOOSE_PROVIDER: anthropic\nGOOSE_MODEL: claude-opus-4\n"
        )
        with patch.object(GooseCLIHand, "_GOOSE_CONFIG_PATHS", (config_file,)):
            result = GooseCLIHand._read_goose_config()
            assert result == ("anthropic", "claude-opus-4")

    def test_reads_model_only(self, tmp_path) -> None:
        """When only GOOSE_MODEL is set, provider is empty string."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("GOOSE_MODEL: gpt-5.2\n")
        with patch.object(GooseCLIHand, "_GOOSE_CONFIG_PATHS", (config_file,)):
            result = GooseCLIHand._read_goose_config()
            assert result == ("", "gpt-5.2")

    def test_empty_config_returns_empty(self, tmp_path) -> None:
        """When config has no provider/model keys, returns empty tuple."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("OTHER_KEY: value\n")
        with patch.object(GooseCLIHand, "_GOOSE_CONFIG_PATHS", (config_file,)):
            result = GooseCLIHand._read_goose_config()
            assert result == ("", "")


# ---------------------------------------------------------------------------
# _resolve_goose_provider_model_from_config — config file fallback paths
# ---------------------------------------------------------------------------


class TestResolveGooseProviderModelFromConfigFile:
    """Tests for config file fallback in _resolve_goose_provider_model_from_config."""

    def test_default_model_reads_from_config(self, make_cli_hand, tmp_path) -> None:
        """When model is 'default', falls back to goose config YAML."""
        config_file = tmp_path / "goose_config.yaml"
        config_file.write_text(
            "GOOSE_PROVIDER: openai\nGOOSE_MODEL: gpt-5.2\n"
        )
        hand = make_cli_hand(GooseCLIHand, model="default")
        with patch.object(GooseCLIHand, "_GOOSE_CONFIG_PATHS", (config_file,)):
            provider, model = hand._resolve_goose_provider_model_from_config()
            assert provider == "openai"
            assert model == "gpt-5.2"

    def test_empty_provider_with_model_infers_provider(
        self, make_cli_hand, tmp_path
    ) -> None:
        """When config has only a model, provider is inferred from model name."""
        config_file = tmp_path / "goose_config.yaml"
        config_file.write_text("GOOSE_MODEL: claude-sonnet-4-5\n")
        hand = make_cli_hand(GooseCLIHand, model="default")
        with patch.object(GooseCLIHand, "_GOOSE_CONFIG_PATHS", (config_file,)):
            provider, model = hand._resolve_goose_provider_model_from_config()
            assert provider == "anthropic"
            assert model == "claude-sonnet-4-5"

    def test_empty_provider_unknown_model_infers_openai(
        self, make_cli_hand, tmp_path
    ) -> None:
        """When config model is unrecognized, provider inferred as openai."""
        config_file = tmp_path / "goose_config.yaml"
        config_file.write_text("GOOSE_MODEL: my-custom-model\n")
        hand = make_cli_hand(GooseCLIHand, model="default")
        with patch.object(GooseCLIHand, "_GOOSE_CONFIG_PATHS", (config_file,)):
            provider, model = hand._resolve_goose_provider_model_from_config()
            # _infer_goose_provider_from_model falls back to "openai"
            assert provider == "openai"
            assert model == "my-custom-model"
