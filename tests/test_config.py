"""Tests for hhpy.helping_hands.lib.config."""

from __future__ import annotations

import os

from hhpy.helping_hands.lib.config import Config


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
