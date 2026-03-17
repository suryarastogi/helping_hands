"""Goose CLI hand implementation."""

from __future__ import annotations

import shutil
from urllib.parse import urlparse

from helping_hands.lib.hands.v1.hand.cli.base import (
    _TwoPhaseCLIHand,
)
from helping_hands.lib.hands.v1.hand.model_provider import (
    _PROVIDER_ANTHROPIC,
    _PROVIDER_GOOGLE,
    _PROVIDER_OLLAMA,
    _PROVIDER_OPENAI,
)

__all__ = ["GooseCLIHand"]

_OLLAMA_DEFAULT_HOST = "http://localhost:11434"
"""Default Ollama API host used when no OLLAMA_HOST or OLLAMA_BASE_URL is set."""


class GooseCLIHand(_TwoPhaseCLIHand):
    """Hand backed by Goose CLI subprocess execution."""

    _BACKEND_NAME = "goose"
    _CLI_LABEL = "goose"
    _CLI_DISPLAY_NAME = "Goose CLI"
    _COMMAND_ENV_VAR = "HELPING_HANDS_GOOSE_CLI_CMD"
    _DEFAULT_CLI_CMD = "goose run --with-builtin developer --text"
    _DEFAULT_MODEL = ""
    _GOOSE_DEFAULT_PROVIDER = _PROVIDER_OLLAMA
    _GOOSE_DEFAULT_MODEL = "llama3.2:latest"

    def _pr_description_cmd(self) -> list[str] | None:
        """Return the CLI command used to generate PR descriptions.

        When the resolved Goose provider is ``anthropic`` and the ``claude``
        binary is available on ``$PATH``, delegates PR description generation
        to the Claude CLI.  Otherwise returns ``None`` to fall back to the
        default provider-based generation.

        Returns:
            Command token list for PR description generation, or ``None``.
        """
        provider, _model = self._resolve_goose_provider_model_from_config()
        if provider == _PROVIDER_ANTHROPIC and shutil.which("claude") is not None:
            return ["claude", "-p", "--output-format", "text"]
        return None

    def _describe_auth(self) -> str:
        """Describe the current authentication configuration for logging.

        Resolves the active Goose provider and checks whether the
        corresponding environment variable (e.g. ``OPENAI_API_KEY``,
        ``ANTHROPIC_API_KEY``) is set.

        Returns:
            Human-readable string summarising provider and auth status.
        """
        import os

        provider, _model = self._resolve_goose_provider_model_from_config()
        env_map = {
            _PROVIDER_OPENAI: "OPENAI_API_KEY",
            _PROVIDER_ANTHROPIC: "ANTHROPIC_API_KEY",
            _PROVIDER_GOOGLE: "GOOGLE_API_KEY",
            _PROVIDER_OLLAMA: "OLLAMA_HOST",
        }
        env_var = env_map.get(provider, provider)
        present = "set" if os.environ.get(env_var, "").strip() else "not set"
        return f"auth=GOOSE_PROVIDER={provider} ({env_var} {present})"

    def _normalize_base_command(self, tokens: list[str]) -> list[str]:
        """Normalize short-form Goose commands to the canonical form.

        Expands bare ``goose``, ``goose run``, and the legacy
        ``goose run --instructions`` forms to the full
        ``goose run --with-builtin developer --text`` invocation.

        Args:
            tokens: Tokenized CLI command list.

        Returns:
            Normalized command token list.
        """
        if tokens == ["goose"]:
            return ["goose", "run", "--with-builtin", "developer", "--text"]
        if tokens == ["goose", "run"]:
            return ["goose", "run", "--with-builtin", "developer", "--text"]
        # Backward compatibility for older local env examples.
        if tokens == ["goose", "run", "--instructions"]:
            return ["goose", "run", "--with-builtin", "developer", "--text"]
        return super()._normalize_base_command(tokens)

    def _resolve_cli_model(self) -> str:
        """Return the CLI model flag value.

        Goose expects provider/model via environment variables
        (``GOOSE_PROVIDER`` / ``GOOSE_MODEL``), not a generic ``--model``
        flag injected by the shared base.  Always returns an empty string
        so the base class skips model injection.

        Returns:
            Empty string (model is set via env vars in
            :meth:`_build_subprocess_env`).
        """
        return ""

    @staticmethod
    def _has_goose_builtin_flag(cmd: list[str]) -> bool:
        """Check whether the command already contains a ``--with-builtin`` flag.

        Args:
            cmd: Tokenized CLI command list.

        Returns:
            ``True`` if any token is ``--with-builtin`` or starts with
            ``--with-builtin=``.
        """
        return any(
            token == "--with-builtin" or token.startswith("--with-builtin=")
            for token in cmd
        )

    def _apply_backend_defaults(self, cmd: list[str]) -> list[str]:
        """Inject ``--with-builtin developer`` if not already present.

        Only applies to ``goose run`` commands that lack a
        ``--with-builtin`` flag.

        Args:
            cmd: Tokenized CLI command list.

        Returns:
            Command list with ``--with-builtin developer`` inserted after
            ``goose run`` when applicable, or the original list unchanged.
        """
        if len(cmd) < 2 or cmd[0] != "goose" or cmd[1] != "run":
            return cmd
        if self._has_goose_builtin_flag(cmd):
            return cmd
        return [*cmd[:2], "--with-builtin", "developer", *cmd[2:]]

    @staticmethod
    def _normalize_goose_provider(provider: str) -> str:
        """Normalize a provider name for Goose configuration.

        Strips whitespace, lowercases, and maps ``"gemini"`` to
        ``"google"`` for Goose compatibility.

        Args:
            provider: Raw provider name string.

        Returns:
            Normalized provider name, or empty string if input is blank.
        """
        value = provider.strip().lower()
        if not value:
            return ""
        if value == "gemini":
            return _PROVIDER_GOOGLE
        return value

    @staticmethod
    def _infer_goose_provider_from_model(model: str) -> str:
        """Infer the Goose provider from a model name prefix.

        Uses well-known model name prefixes (``claude`` → ``anthropic``,
        ``gemini`` → ``google``, ``llama`` → ``ollama``) to determine the
        provider.  Falls back to ``"openai"`` for unrecognised models.

        Args:
            model: Model name string (e.g. ``"claude-sonnet-4-5"``).

        Returns:
            Inferred provider name string.
        """
        lowered = model.strip().lower()
        if lowered.startswith(("claude", "anthropic/")):
            return _PROVIDER_ANTHROPIC
        if lowered.startswith(("gemini", "google/")):
            return _PROVIDER_GOOGLE
        if lowered.startswith(("llama", "ollama/")):
            return _PROVIDER_OLLAMA
        return _PROVIDER_OPENAI

    @staticmethod
    def _normalize_ollama_host(value: str) -> str:
        """Normalize and validate an Ollama host URL.

        Strips whitespace, prepends ``http://`` if no scheme is present,
        and validates that the resulting URL has an ``http`` or ``https``
        scheme with a non-empty netloc.

        Args:
            value: Raw host URL string.

        Returns:
            Normalized ``scheme://netloc`` string, or empty string if
            the input is blank or invalid.
        """
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
        """Resolve the Ollama API host from environment variables.

        Checks ``OLLAMA_HOST`` first, then ``OLLAMA_BASE_URL``, falling
        back to :data:`_OLLAMA_DEFAULT_HOST` if neither is set or valid.

        Args:
            env: Environment variable mapping.

        Returns:
            Resolved Ollama host URL string.
        """
        explicit_host = cls._normalize_ollama_host(env.get("OLLAMA_HOST", ""))
        if explicit_host:
            return explicit_host
        from_base_url = cls._normalize_ollama_host(env.get("OLLAMA_BASE_URL", ""))
        if from_base_url:
            return from_base_url
        return _OLLAMA_DEFAULT_HOST

    def _resolve_goose_provider_model_from_config(self) -> tuple[str, str]:
        """Resolve the Goose provider and model from the hand configuration.

        Parses ``config.model`` using ``provider/model`` format when a
        slash is present, otherwise infers the provider from the model
        name.  Returns class defaults when the model is empty or
        ``"default"``.

        Returns:
            ``(provider, model)`` tuple.
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
        if not provider:
            provider = self._infer_goose_provider_from_model(model)
        return provider, model

    def _build_subprocess_env(self) -> dict[str, str]:
        """Build the environment variables dict for the Goose subprocess.

        Extends the base environment with Goose-specific variables:
        ``GOOSE_PROVIDER``, ``GOOSE_MODEL``, and ``OLLAMA_HOST`` (when
        the provider is ``ollama``).  Validates that a GitHub token is
        available.

        Returns:
            Environment variable mapping for ``subprocess.Popen``.

        Raises:
            RuntimeError: If neither ``GH_TOKEN`` nor ``GITHUB_TOKEN``
                is set in the environment.
        """
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
        if resolved_provider == _PROVIDER_OLLAMA:
            env["OLLAMA_HOST"] = self._resolve_ollama_host(env)
        return env
