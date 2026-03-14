"""Tests for helping_hands.lib.config."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import helping_hands.lib.config as config_module
from helping_hands.lib.config import VALID_BACKENDS, Config


class TestConfigDefaults:
    def test_defaults(self) -> None:
        config = Config()
        assert config.repo == ""
        assert config.model == "default"
        assert config.backend == "langgraph"
        assert config.verbose is False

    def test_from_env_picks_up_env_var(self, monkeypatch: object) -> None:
        os.environ["HELPING_HANDS_MODEL"] = "gpt-test"
        try:
            config = Config.from_env()
            assert config.model == "gpt-test"
        finally:
            del os.environ["HELPING_HANDS_MODEL"]

    def test_overrides_beat_env(self) -> None:
        os.environ["HELPING_HANDS_MODEL"] = "from-env"
        try:
            config = Config.from_env(overrides={"model": "from-cli"})
            assert config.model == "from-cli"
        finally:
            del os.environ["HELPING_HANDS_MODEL"]

    def test_from_env_loads_dotenv(self, tmp_path: Path, monkeypatch: object) -> None:
        loaded_paths: list[Path] = []
        env_file = tmp_path / ".env"
        env_file.write_text("HELPING_HANDS_MODEL=from-dotenv\n")

        def fake_load_dotenv(path: Path, override: bool = False) -> bool:
            loaded_paths.append(path)
            if path == env_file:
                os.environ["HELPING_HANDS_MODEL"] = "from-dotenv"
            return True

        if "HELPING_HANDS_MODEL" in os.environ:
            del os.environ["HELPING_HANDS_MODEL"]
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(config_module, "load_dotenv", fake_load_dotenv)

        try:
            config = Config.from_env()
            assert config.model == "from-dotenv"
            assert env_file in loaded_paths
        finally:
            if "HELPING_HANDS_MODEL" in os.environ:
                del os.environ["HELPING_HANDS_MODEL"]


class TestConfigBackend:
    def test_default_backend(self) -> None:
        config = Config.from_env()
        assert config.backend == "langgraph"

    def test_backend_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_BACKEND", "claudecode")
        config = Config.from_env()
        assert config.backend == "claudecode"

    def test_backend_from_override(self) -> None:
        config = Config.from_env(overrides={"backend": "atomic"})
        assert config.backend == "atomic"

    def test_override_beats_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_BACKEND", "langgraph")
        config = Config.from_env(overrides={"backend": "claudecode"})
        assert config.backend == "claudecode"

    def test_invalid_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid backend"):
            Config.from_env(overrides={"backend": "nonexistent"})

    def test_all_valid_backends_accepted(self) -> None:
        for backend in VALID_BACKENDS:
            config = Config.from_env(overrides={"backend": backend})
            assert config.backend == backend
