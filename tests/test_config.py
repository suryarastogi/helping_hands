"""Tests for helping_hands.lib.config."""

from __future__ import annotations

import os
from pathlib import Path

import helping_hands.lib.config as config_module
from helping_hands.lib.config import Config


class TestConfigDefaults:
    def test_defaults(self) -> None:
        config = Config()
        assert config.repo == ""
        assert config.model == "default"
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
