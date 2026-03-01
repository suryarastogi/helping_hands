"""Tests for CLI hand implementations (claude, codex, goose, gemini)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand
from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand
from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand
from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def config() -> Config:
    return Config(repo="/tmp/fake", model="test-model")


@pytest.fixture()
def repo_index(tmp_path: Path) -> RepoIndex:
    (tmp_path / "main.py").write_text("")
    return RepoIndex.from_path(tmp_path)


def _make_hand(cls: type, config: Config, repo_index: RepoIndex) -> Any:
    return cls(config, repo_index)


# ===========================================================================
# ClaudeCodeHand
# ===========================================================================


class TestClaudeCodeHandModelFiltering:
    """Model filtering drops GPT-family models for Claude CLI."""

    def test_gpt_model_dropped(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="gpt-5.2")
        hand = _make_hand(ClaudeCodeHand, cfg, repo_index)
        assert hand._resolve_cli_model() == ""

    def test_claude_model_kept(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="claude-sonnet-4-5")
        hand = _make_hand(ClaudeCodeHand, cfg, repo_index)
        assert hand._resolve_cli_model() == "claude-sonnet-4-5"

    def test_provider_prefix_stripped(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="anthropic/claude-sonnet-4-5")
        hand = _make_hand(ClaudeCodeHand, cfg, repo_index)
        assert hand._resolve_cli_model() == "claude-sonnet-4-5"

    def test_default_model_returns_empty(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="default")
        hand = _make_hand(ClaudeCodeHand, cfg, repo_index)
        assert hand._resolve_cli_model() == ""

    def test_empty_model_returns_empty(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="")
        hand = _make_hand(ClaudeCodeHand, cfg, repo_index)
        assert hand._resolve_cli_model() == ""


class TestClaudeCodeHandSkipPermissions:
    """--dangerously-skip-permissions logic."""

    def test_enabled_by_default_non_root(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        with (
            patch.dict(
                "os.environ",
                {"HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS": "1"},
            ),
            patch("os.geteuid", return_value=1000),
        ):
            assert hand._skip_permissions_enabled() is True

    def test_disabled_for_root(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        with (
            patch.dict(
                "os.environ",
                {"HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS": "1"},
            ),
            patch("os.geteuid", return_value=0),
        ):
            assert hand._skip_permissions_enabled() is False

    def test_disabled_by_env_var(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        with patch.dict(
            "os.environ",
            {"HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS": "0"},
        ):
            assert hand._skip_permissions_enabled() is False

    def test_apply_backend_defaults_injects_flag(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        with patch.object(hand, "_skip_permissions_enabled", return_value=True):
            cmd = hand._apply_backend_defaults(["claude", "-p", "hello"])
            assert "--dangerously-skip-permissions" in cmd

    def test_apply_backend_defaults_skips_non_claude(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        with patch.object(hand, "_skip_permissions_enabled", return_value=True):
            cmd = hand._apply_backend_defaults(["npx", "-y", "@anthropic-ai/claude-code", "-p", "hello"])
            assert "--dangerously-skip-permissions" not in cmd

    def test_apply_backend_defaults_no_double_inject(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        with patch.object(hand, "_skip_permissions_enabled", return_value=True):
            cmd = hand._apply_backend_defaults(
                ["claude", "--dangerously-skip-permissions", "-p", "hello"]
            )
            assert cmd.count("--dangerously-skip-permissions") == 1


class TestClaudeCodeHandRetry:
    """Retry and fallback logic."""

    def test_retry_strips_permission_flag_on_root_error(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        cmd = ["claude", "--dangerously-skip-permissions", "-p", "hello"]
        result = hand._retry_command_after_failure(
            cmd,
            output="Error: --dangerously-skip-permissions cannot be used with root/sudo privileges",
            return_code=1,
        )
        assert result is not None
        assert "--dangerously-skip-permissions" not in result

    def test_retry_returns_none_without_flag(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        cmd = ["claude", "-p", "hello"]
        result = hand._retry_command_after_failure(
            cmd,
            output="some error",
            return_code=1,
        )
        assert result is None

    def test_retry_returns_none_on_success(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        cmd = ["claude", "--dangerously-skip-permissions", "-p", "hello"]
        result = hand._retry_command_after_failure(
            cmd,
            output="success",
            return_code=0,
        )
        assert result is None

    def test_fallback_to_npx(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        with patch("shutil.which", return_value="/usr/bin/npx"):
            result = hand._fallback_command_when_not_found(["claude", "-p", "hello"])
        assert result is not None
        assert result[0] == "npx"
        assert "@anthropic-ai/claude-code" in result

    def test_no_fallback_without_npx(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        with patch("shutil.which", return_value=None):
            result = hand._fallback_command_when_not_found(["claude", "-p", "hello"])
        assert result is None

    def test_no_fallback_for_non_claude_command(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        result = hand._fallback_command_when_not_found(["some-other", "-p", "hello"])
        assert result is None


class TestClaudeCodeHandFailureMessages:
    """Failure message parsing."""

    def test_auth_failure_detected(self) -> None:
        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1,
            output="Error: 401 Unauthorized - invalid API key",
        )
        assert "authentication failed" in msg.lower()

    def test_generic_failure(self) -> None:
        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1,
            output="Something went wrong",
        )
        assert "exit=1" in msg

    def test_anthropic_api_key_detected(self) -> None:
        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1,
            output="Missing ANTHROPIC_API_KEY in environment",
        )
        assert "ANTHROPIC_API_KEY" in msg


class TestClaudeCodeHandPermissionPromptDetection:
    """No-change error detection from permission prompts."""

    def test_permission_prompt_detected(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        output = "The write permissions to this file haven't been granted yet"
        result = hand._no_change_error_after_retries(
            prompt="update file",
            combined_output=output,
        )
        assert result is not None
        assert "write permission" in result.lower()

    def test_no_permission_prompt_returns_none(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        result = hand._no_change_error_after_retries(
            prompt="update file",
            combined_output="All good, no issues",
        )
        assert result is None


class TestClaudeCodeHandNativeAuth:
    """Native CLI auth env name."""

    def test_native_auth_env_names(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        assert "ANTHROPIC_API_KEY" in hand._native_cli_auth_env_names()


# ===========================================================================
# CodexCLIHand
# ===========================================================================


class TestCodexCLIHandModel:
    """Default model and base command normalization."""

    def test_default_model_is_gpt52(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="default")
        hand = _make_hand(CodexCLIHand, cfg, repo_index)
        assert hand._resolve_cli_model() == "gpt-5.2"

    def test_custom_model_passed_through(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="gpt-4o")
        hand = _make_hand(CodexCLIHand, cfg, repo_index)
        assert hand._resolve_cli_model() == "gpt-4o"

    def test_normalize_bare_codex(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(CodexCLIHand, config, repo_index)
        result = hand._normalize_base_command(["codex"])
        assert result == ["codex", "exec"]


class TestCodexCLIHandSandbox:
    """Sandbox mode auto-detection."""

    def test_host_sandbox_mode(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(CodexCLIHand, config, repo_index)
        with patch.object(Path, "exists", return_value=False):
            assert hand._auto_sandbox_mode() == "workspace-write"

    def test_container_sandbox_mode(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(CodexCLIHand, config, repo_index)
        with patch.object(Path, "exists", return_value=True):
            assert hand._auto_sandbox_mode() == "danger-full-access"

    def test_sandbox_injected_for_codex_exec(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(CodexCLIHand, config, repo_index)
        with patch.dict("os.environ", {}, clear=False):
            if "HELPING_HANDS_CODEX_SANDBOX_MODE" in __import__("os").environ:
                del __import__("os").environ["HELPING_HANDS_CODEX_SANDBOX_MODE"]
            cmd = hand._apply_codex_exec_sandbox_defaults(
                ["codex", "exec", "do something"]
            )
            assert "--sandbox" in cmd

    def test_sandbox_not_injected_when_already_present(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(CodexCLIHand, config, repo_index)
        cmd = hand._apply_codex_exec_sandbox_defaults(
            ["codex", "exec", "--sandbox", "custom-mode", "do something"]
        )
        assert cmd.count("--sandbox") == 1

    def test_sandbox_not_injected_for_non_exec(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(CodexCLIHand, config, repo_index)
        cmd = hand._apply_codex_exec_sandbox_defaults(
            ["codex", "chat", "do something"]
        )
        assert "--sandbox" not in cmd

    def test_sandbox_mode_env_override(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(CodexCLIHand, config, repo_index)
        with patch.dict(
            "os.environ",
            {"HELPING_HANDS_CODEX_SANDBOX_MODE": "custom-mode"},
        ):
            cmd = hand._apply_codex_exec_sandbox_defaults(
                ["codex", "exec", "do something"]
            )
            assert "--sandbox" in cmd
            sandbox_idx = cmd.index("--sandbox")
            assert cmd[sandbox_idx + 1] == "custom-mode"


class TestCodexCLIHandGitRepoCheck:
    """Skip git repo check injection."""

    def test_skip_git_repo_check_default_enabled(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(CodexCLIHand, config, repo_index)
        with patch.dict("os.environ", {}, clear=False):
            if "HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK" in __import__("os").environ:
                del __import__("os").environ["HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK"]
            assert hand._skip_git_repo_check_enabled() is True

    def test_skip_git_repo_check_disabled_by_env(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(CodexCLIHand, config, repo_index)
        with patch.dict(
            "os.environ",
            {"HELPING_HANDS_CODEX_SKIP_GIT_REPO_CHECK": "0"},
        ):
            assert hand._skip_git_repo_check_enabled() is False

    def test_skip_flag_injected(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(CodexCLIHand, config, repo_index)
        with patch.object(hand, "_skip_git_repo_check_enabled", return_value=True):
            cmd = hand._apply_codex_exec_git_repo_check_defaults(
                ["codex", "exec", "do something"]
            )
            assert "--skip-git-repo-check" in cmd

    def test_skip_flag_not_doubled(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(CodexCLIHand, config, repo_index)
        with patch.object(hand, "_skip_git_repo_check_enabled", return_value=True):
            cmd = hand._apply_codex_exec_git_repo_check_defaults(
                ["codex", "exec", "--skip-git-repo-check", "do something"]
            )
            assert cmd.count("--skip-git-repo-check") == 1


class TestCodexCLIHandFailureMessages:
    """Failure message parsing."""

    def test_auth_failure_detected(self) -> None:
        msg = CodexCLIHand._build_codex_failure_message(
            return_code=1,
            output="Error: 401 Unauthorized - missing bearer or basic authentication",
        )
        assert "authentication failed" in msg.lower()

    def test_generic_failure(self) -> None:
        msg = CodexCLIHand._build_codex_failure_message(
            return_code=1,
            output="Something went wrong",
        )
        assert "exit=1" in msg


class TestCodexCLIHandNativeAuth:
    """Native CLI auth env name."""

    def test_native_auth_env_names(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(CodexCLIHand, config, repo_index)
        assert "OPENAI_API_KEY" in hand._native_cli_auth_env_names()


# ===========================================================================
# GooseCLIHand
# ===========================================================================


class TestGooseCLIHandProviderModel:
    """Provider and model resolution from config."""

    def test_default_provider_is_ollama(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="default")
        hand = _make_hand(GooseCLIHand, cfg, repo_index)
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == "ollama"
        assert model == "llama3.2:latest"

    def test_empty_model_defaults(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="")
        hand = _make_hand(GooseCLIHand, cfg, repo_index)
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == "ollama"
        assert model == "llama3.2:latest"

    def test_gpt_model_infers_openai(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="gpt-5.2")
        hand = _make_hand(GooseCLIHand, cfg, repo_index)
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == "openai"
        assert model == "gpt-5.2"

    def test_claude_model_infers_anthropic(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="claude-sonnet-4-5")
        hand = _make_hand(GooseCLIHand, cfg, repo_index)
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == "anthropic"
        assert model == "claude-sonnet-4-5"

    def test_gemini_model_infers_google(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="gemini-2.0-flash")
        hand = _make_hand(GooseCLIHand, cfg, repo_index)
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == "google"
        assert model == "gemini-2.0-flash"

    def test_explicit_provider_prefix(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="anthropic/claude-sonnet-4-5")
        hand = _make_hand(GooseCLIHand, cfg, repo_index)
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == "anthropic"
        assert model == "claude-sonnet-4-5"

    def test_llama_model_infers_ollama(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="llama3.2:latest")
        hand = _make_hand(GooseCLIHand, cfg, repo_index)
        provider, model = hand._resolve_goose_provider_model_from_config()
        assert provider == "ollama"
        assert model == "llama3.2:latest"


class TestGooseCLIHandOllamaHost:
    """Ollama host normalization."""

    def test_plain_host_gets_http_prefix(self) -> None:
        assert GooseCLIHand._normalize_ollama_host("localhost:11434") == "http://localhost:11434"

    def test_http_url_preserved(self) -> None:
        assert GooseCLIHand._normalize_ollama_host("http://192.168.1.143:11434") == "http://192.168.1.143:11434"

    def test_https_url_preserved(self) -> None:
        assert GooseCLIHand._normalize_ollama_host("https://ollama.example.com") == "https://ollama.example.com"

    def test_empty_returns_empty(self) -> None:
        assert GooseCLIHand._normalize_ollama_host("") == ""

    def test_whitespace_returns_empty(self) -> None:
        assert GooseCLIHand._normalize_ollama_host("   ") == ""

    def test_resolve_default_localhost(self) -> None:
        result = GooseCLIHand._resolve_ollama_host({})
        assert result == "http://localhost:11434"

    def test_resolve_from_ollama_host(self) -> None:
        result = GooseCLIHand._resolve_ollama_host(
            {"OLLAMA_HOST": "http://custom:11434"}
        )
        assert result == "http://custom:11434"

    def test_resolve_from_base_url_fallback(self) -> None:
        result = GooseCLIHand._resolve_ollama_host(
            {"OLLAMA_BASE_URL": "http://fallback:11434"}
        )
        assert result == "http://fallback:11434"


class TestGooseCLIHandGitHubToken:
    """GitHub token requirement."""

    def test_missing_token_raises(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GooseCLIHand, config, repo_index)
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(RuntimeError, match="GH_TOKEN or GITHUB_TOKEN"),
        ):
            hand._build_subprocess_env()

    def test_gh_token_mirrored(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GooseCLIHand, config, repo_index)
        with patch.dict(
            "os.environ",
            {"GH_TOKEN": "tok123", "GITHUB_TOKEN": "", "PATH": "/usr/bin"},
            clear=True,
        ):
            env = hand._build_subprocess_env()
            assert env["GH_TOKEN"] == "tok123"
            assert env["GITHUB_TOKEN"] == "tok123"

    def test_github_token_mirrored(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GooseCLIHand, config, repo_index)
        with patch.dict(
            "os.environ",
            {"GH_TOKEN": "", "GITHUB_TOKEN": "tok456", "PATH": "/usr/bin"},
            clear=True,
        ):
            env = hand._build_subprocess_env()
            assert env["GH_TOKEN"] == "tok456"
            assert env["GITHUB_TOKEN"] == "tok456"


class TestGooseCLIHandBackendDefaults:
    """--with-builtin developer injection."""

    def test_builtin_injected_for_goose_run(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GooseCLIHand, config, repo_index)
        cmd = hand._apply_backend_defaults(["goose", "run", "--text", "hello"])
        assert "--with-builtin" in cmd
        builtin_idx = cmd.index("--with-builtin")
        assert cmd[builtin_idx + 1] == "developer"

    def test_builtin_not_doubled(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GooseCLIHand, config, repo_index)
        cmd = hand._apply_backend_defaults(
            ["goose", "run", "--with-builtin", "developer", "--text", "hello"]
        )
        assert cmd.count("--with-builtin") == 1

    def test_builtin_skipped_for_non_run(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GooseCLIHand, config, repo_index)
        cmd = hand._apply_backend_defaults(["goose", "chat", "hello"])
        assert "--with-builtin" not in cmd


class TestGooseCLIHandNormalizeBase:
    """Base command normalization."""

    def test_bare_goose_expanded(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GooseCLIHand, config, repo_index)
        result = hand._normalize_base_command(["goose"])
        assert result == ["goose", "run", "--with-builtin", "developer", "--text"]

    def test_goose_run_expanded(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GooseCLIHand, config, repo_index)
        result = hand._normalize_base_command(["goose", "run"])
        assert result == ["goose", "run", "--with-builtin", "developer", "--text"]


class TestGooseCLIHandProviderNormalization:
    """Provider name normalization."""

    def test_gemini_maps_to_google(self) -> None:
        assert GooseCLIHand._normalize_goose_provider("gemini") == "google"

    def test_openai_passthrough(self) -> None:
        assert GooseCLIHand._normalize_goose_provider("openai") == "openai"

    def test_empty_returns_empty(self) -> None:
        assert GooseCLIHand._normalize_goose_provider("") == ""

    def test_case_insensitive(self) -> None:
        assert GooseCLIHand._normalize_goose_provider("GEMINI") == "google"


class TestGooseCLIHandProviderInference:
    """Provider inference from model name."""

    def test_claude_infers_anthropic(self) -> None:
        assert GooseCLIHand._infer_goose_provider_from_model("claude-3-5-sonnet") == "anthropic"

    def test_gemini_infers_google(self) -> None:
        assert GooseCLIHand._infer_goose_provider_from_model("gemini-2.0-flash") == "google"

    def test_llama_infers_ollama(self) -> None:
        assert GooseCLIHand._infer_goose_provider_from_model("llama3.2:latest") == "ollama"

    def test_gpt_infers_openai(self) -> None:
        assert GooseCLIHand._infer_goose_provider_from_model("gpt-5.2") == "openai"

    def test_unknown_defaults_to_openai(self) -> None:
        assert GooseCLIHand._infer_goose_provider_from_model("custom-model") == "openai"


class TestGooseCLIHandModelResolution:
    """Model resolution for CLI (always empty — Goose uses env vars)."""

    def test_cli_model_always_empty(self, repo_index: RepoIndex) -> None:
        cfg = Config(repo="/tmp/fake", model="gpt-5.2")
        hand = _make_hand(GooseCLIHand, cfg, repo_index)
        assert hand._resolve_cli_model() == ""


# ===========================================================================
# GeminiCLIHand
# ===========================================================================


class TestGeminiCLIHandApprovalMode:
    """--approval-mode auto_edit injection."""

    def test_approval_mode_injected(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GeminiCLIHand, config, repo_index)
        cmd = hand._apply_backend_defaults(["gemini", "-p", "hello"])
        assert "--approval-mode" in cmd
        idx = cmd.index("--approval-mode")
        assert cmd[idx + 1] == "auto_edit"

    def test_approval_mode_not_doubled(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GeminiCLIHand, config, repo_index)
        cmd = hand._apply_backend_defaults(
            ["gemini", "--approval-mode", "custom", "-p", "hello"]
        )
        assert cmd.count("--approval-mode") == 1

    def test_approval_mode_skipped_for_non_gemini(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GeminiCLIHand, config, repo_index)
        cmd = hand._apply_backend_defaults(["other-cli", "-p", "hello"])
        assert "--approval-mode" not in cmd


class TestGeminiCLIHandModelNotFound:
    """Model-not-found detection and retry."""

    def test_model_not_found_detected(self) -> None:
        assert GeminiCLIHand._looks_like_model_not_found(
            "ModelNotFoundError: models/gemini-1.5-flash is no longer available"
        )

    def test_model_not_found_by_keyword(self) -> None:
        assert GeminiCLIHand._looks_like_model_not_found(
            "Error: models/gemini-old not found"
        )

    def test_normal_output_not_detected(self) -> None:
        assert not GeminiCLIHand._looks_like_model_not_found(
            "Task completed successfully"
        )

    def test_extract_model_name(self) -> None:
        model = GeminiCLIHand._extract_unavailable_model(
            "Error: models/gemini-1.5-flash is unavailable"
        )
        assert model == "gemini-1.5-flash"

    def test_extract_model_name_empty(self) -> None:
        model = GeminiCLIHand._extract_unavailable_model("No model here")
        assert model == ""

    def test_strip_model_args(self) -> None:
        result = GeminiCLIHand._strip_model_args(
            ["gemini", "--model", "old-model", "-p", "hello"]
        )
        assert result is not None
        assert "--model" not in result
        assert "old-model" not in result

    def test_strip_model_args_equals_form(self) -> None:
        result = GeminiCLIHand._strip_model_args(
            ["gemini", "--model=old-model", "-p", "hello"]
        )
        assert result is not None
        assert "--model=old-model" not in result

    def test_strip_model_args_none_when_missing(self) -> None:
        result = GeminiCLIHand._strip_model_args(["gemini", "-p", "hello"])
        assert result is None

    def test_retry_on_model_not_found(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GeminiCLIHand, config, repo_index)
        result = hand._retry_command_after_failure(
            ["gemini", "--model", "old", "-p", "hello"],
            output="ModelNotFoundError: models/old is no longer available",
            return_code=1,
        )
        assert result is not None
        assert "--model" not in result

    def test_no_retry_on_success(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GeminiCLIHand, config, repo_index)
        result = hand._retry_command_after_failure(
            ["gemini", "--model", "ok", "-p", "hello"],
            output="Done",
            return_code=0,
        )
        assert result is None


class TestGeminiCLIHandApiKey:
    """API key requirement."""

    def test_missing_api_key_raises(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GeminiCLIHand, config, repo_index)
        with (
            patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=True),
            pytest.raises(RuntimeError, match="GEMINI_API_KEY"),
        ):
            hand._build_subprocess_env()

    def test_api_key_present_passes(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(GeminiCLIHand, config, repo_index)
        with patch.dict(
            "os.environ",
            {"GEMINI_API_KEY": "test-key", "PATH": "/usr/bin"},
            clear=True,
        ):
            env = hand._build_subprocess_env()
            assert env["GEMINI_API_KEY"] == "test-key"


class TestGeminiCLIHandFailureMessages:
    """Failure message parsing."""

    def test_auth_failure_detected(self) -> None:
        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=1,
            output="Error: api key not valid for this project",
        )
        assert "authentication failed" in msg.lower()

    def test_model_unavailable_detected(self) -> None:
        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=1,
            output="ModelNotFoundError: models/old-model is no longer available to new users",
        )
        assert "unavailable" in msg.lower()

    def test_generic_failure(self) -> None:
        msg = GeminiCLIHand._build_gemini_failure_message(
            return_code=1,
            output="Something went wrong",
        )
        assert "exit=1" in msg


# ===========================================================================
# Shared _TwoPhaseCLIHand base tests via concrete subclasses
# ===========================================================================


class TestTwoPhaseCLIHandBase:
    """Shared base logic tested through concrete subclasses."""

    def test_truncate_summary_short(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        assert hand._truncate_summary("hello", limit=100) == "hello"

    def test_truncate_summary_long(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        long_text = "x" * 200
        result = hand._truncate_summary(long_text, limit=50)
        assert len(result) < 200
        assert "truncated" in result

    def test_is_truthy_values(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        assert hand._is_truthy("1") is True
        assert hand._is_truthy("true") is True
        assert hand._is_truthy("yes") is True
        assert hand._is_truthy("on") is True
        assert hand._is_truthy("0") is False
        assert hand._is_truthy("false") is False
        assert hand._is_truthy("") is False
        assert hand._is_truthy(None) is False

    def test_looks_like_edit_request(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        assert hand._looks_like_edit_request("Update the README") is True
        assert hand._looks_like_edit_request("Fix the bug in X") is True
        assert hand._looks_like_edit_request("Tell me about Python") is False

    def test_float_env_default(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        with patch.dict("os.environ", {}, clear=False):
            result = hand._float_env("NONEXISTENT_VAR", default=42.0)
            assert result == 42.0

    def test_float_env_valid(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        with patch.dict("os.environ", {"TEST_FLOAT": "3.5"}):
            result = hand._float_env("TEST_FLOAT", default=1.0)
            assert result == 3.5

    def test_float_env_invalid_returns_default(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        with patch.dict("os.environ", {"TEST_FLOAT": "not-a-number"}):
            result = hand._float_env("TEST_FLOAT", default=1.0)
            assert result == 1.0

    def test_float_env_negative_returns_default(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        with patch.dict("os.environ", {"TEST_FLOAT": "-5"}):
            result = hand._float_env("TEST_FLOAT", default=1.0)
            assert result == 1.0

    def test_build_init_prompt_contains_repo_root(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        prompt = hand._build_init_prompt()
        assert str(repo_index.root) in prompt
        assert "Initialization phase" in prompt

    def test_build_task_prompt_contains_user_request(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        prompt = hand._build_task_prompt(
            prompt="Implement feature X",
            learned_summary="Repo uses Python 3.12",
        )
        assert "Implement feature X" in prompt
        assert "Repo uses Python 3.12" in prompt

    def test_build_apply_changes_prompt(
        self, config: Config, repo_index: RepoIndex
    ) -> None:
        hand = _make_hand(ClaudeCodeHand, config, repo_index)
        prompt = hand._build_apply_changes_prompt(
            prompt="Fix the bug",
            task_output="I described the fix but didn't apply it",
        )
        assert "Fix the bug" in prompt
        assert "enforcement" in prompt.lower()
