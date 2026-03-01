"""Goose CLI hand implementation."""

from __future__ import annotations

__all__ = ["GooseCLIHand"]

import shutil
from urllib.parse import urlparse

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand


class GooseCLIHand(_TwoPhaseCLIHand):
    """Hand backed by Goose CLI subprocess execution."""

    _BACKEND_NAME = "goose"
    _CLI_LABEL = "goose"
    _CLI_DISPLAY_NAME = "Goose CLI"
    _COMMAND_ENV_VAR = "HELPING_HANDS_GOOSE_CLI_CMD"
    _DEFAULT_CLI_CMD = "goose run --with-builtin developer --text"
    _DEFAULT_MODEL = ""
    _GOOSE_DEFAULT_PROVIDER = "ollama"
    _GOOSE_DEFAULT_MODEL = "llama3.2:latest"

    def _pr_description_cmd(self) -> list[str] | None:
        provider, _model = self._resolve_goose_provider_model_from_config()
        if provider == "anthropic" and shutil.which("claude") is not None:
            return ["claude", "-p", "--output-format", "text"]
        return None

    def _describe_auth(self) -> str:
        import os

        provider, _model = self._resolve_goose_provider_model_from_config()
        env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "ollama": "OLLAMA_HOST",
        }
        env_var = env_map.get(provider, provider)
        present = "set" if os.environ.get(env_var, "").strip() else "not set"
        return f"auth=GOOSE_PROVIDER={provider} ({env_var} {present})"

    def _normalize_base_command(self, tokens: list[str]) -> list[str]:
        if tokens == ["goose"]:
            return ["goose", "run", "--with-builtin", "developer", "--text"]
        if tokens == ["goose", "run"]:
            return ["goose", "run", "--with-builtin", "developer", "--text"]
        # Backward compatibility for older local env examples.
        if tokens == ["goose", "run", "--instructions"]:
            return ["goose", "run", "--with-builtin", "developer", "--text"]
        return super()._normalize_base_command(tokens)

    def _resolve_cli_model(self) -> str:
        # Goose expects provider/model via env vars (GOOSE_PROVIDER/GOOSE_MODEL),
        # not a generic CLI --model flag injected by the shared base.
        return ""

    @staticmethod
    def _has_goose_builtin_flag(cmd: list[str]) -> bool:
        """Return True if *cmd* already contains a ``--with-builtin`` flag."""
        return any(
            token == "--with-builtin" or token.startswith("--with-builtin=")
            for token in cmd
        )

    def _apply_backend_defaults(self, cmd: list[str]) -> list[str]:
        """Inject ``--with-builtin developer`` for ``goose run`` when missing."""
        if len(cmd) < 2 or cmd[0] != "goose" or cmd[1] != "run":
            return cmd
        if self._has_goose_builtin_flag(cmd):
            return cmd
        return [*cmd[:2], "--with-builtin", "developer", *cmd[2:]]

    def _command_not_found_message(self, command: str) -> str:
        return (
            f"Goose CLI command not found: {command!r}. "
            "Set HELPING_HANDS_GOOSE_CLI_CMD to a valid command. "
            "If running app mode in Docker, rebuild worker images so "
            "the goose binary is installed."
        )

    @staticmethod
    def _normalize_goose_provider(provider: str) -> str:
        """Normalize a provider string, mapping ``gemini`` to ``google``."""
        value = provider.strip().lower()
        if not value:
            return ""
        if value == "gemini":
            return "google"
        return value

    @staticmethod
    def _infer_goose_provider_from_model(model: str) -> str:
        """Infer the Goose provider from a model name prefix (e.g. ``claude`` -> ``anthropic``)."""
        lowered = model.strip().lower()
        if lowered.startswith(("claude", "anthropic/")):
            return "anthropic"
        if lowered.startswith(("gemini", "google/")):
            return "google"
        if lowered.startswith(("llama", "ollama/")):
            return "ollama"
        return "openai"

    @staticmethod
    def _normalize_ollama_host(value: str) -> str:
        """Normalize an Ollama host URL, prepending ``http://`` if no scheme is present."""
        candidate = value.strip()
        if not candidate:
            return ""
        if "://" not in candidate:
            candidate = f"http://{candidate}"
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        return f"{parsed.scheme}://{parsed.netloc}"

    @classmethod
    def _resolve_ollama_host(cls, env: dict[str, str]) -> str:
        """Resolve the Ollama host from ``OLLAMA_HOST``, ``OLLAMA_BASE_URL``, or default."""
        explicit_host = cls._normalize_ollama_host(env.get("OLLAMA_HOST", ""))
        if explicit_host:
            return explicit_host
        from_base_url = cls._normalize_ollama_host(env.get("OLLAMA_BASE_URL", ""))
        if from_base_url:
            return from_base_url
        return "http://localhost:11434"

    def _resolve_goose_provider_model_from_config(self) -> tuple[str, str]:
        """Derive ``(provider, model)`` for Goose from the ``config.model`` string.

        Supports bare model names (inferred provider), explicit ``provider/model``
        format, and defaults to ``ollama/llama3.2:latest`` when unset.
        """
        raw_model = str(self.config.model).strip()
        if not raw_model or raw_model == "default":
            return self._GOOSE_DEFAULT_PROVIDER, self._GOOSE_DEFAULT_MODEL

        provider = ""
        model = raw_model
        if "/" in raw_model:
            provider_prefix, _, provider_model = raw_model.partition("/")
            if provider_model:
                provider = self._normalize_goose_provider(provider_prefix)
                model = provider_model.strip()
        if not model:
            model = self._GOOSE_DEFAULT_MODEL
        if not provider:
            provider = self._infer_goose_provider_from_model(model)
        return provider, model

    def _build_subprocess_env(self) -> dict[str, str]:
        """Build env for Goose subprocess with provider/model and GitHub token injection."""
        env = super()._build_subprocess_env()
        gh_token = env.get("GH_TOKEN", "").strip()
        github_token = env.get("GITHUB_TOKEN", "").strip()
        token = gh_token or github_token
        if not token:
            msg = (
                "Goose backend requires GH_TOKEN or GITHUB_TOKEN. "
                "Set one of these env vars; local GitHub auth fallback is disabled."
            )
            raise RuntimeError(msg)
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token

        default_provider, default_model = (
            self._resolve_goose_provider_model_from_config()
        )
        goose_model = env.get("GOOSE_MODEL", "").strip() or default_model
        goose_provider = self._normalize_goose_provider(env.get("GOOSE_PROVIDER", ""))
        if not goose_provider:
            goose_provider = self._infer_goose_provider_from_model(goose_model)
        resolved_provider = goose_provider or default_provider
        env["GOOSE_PROVIDER"] = resolved_provider
        env["GOOSE_MODEL"] = goose_model
        if resolved_provider == "ollama":
            env["OLLAMA_HOST"] = self._resolve_ollama_host(env)
        return env
