from pathlib import Path

import pytest

from local_ai_dev_tools.ai_commit.config import (
    DEFAULT_MODEL,
    ConfigError,
    resolve_model,
)


def test_cli_model_wins(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('[ai_commit]\nmodel = "config-model"\n')

    assert resolve_model("cli-model", config_path) == "cli-model"


def test_config_model_wins_over_default(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('[ai_commit]\nmodel = "config-model"\n')

    assert resolve_model(None, config_path) == "config-model"


def test_default_model_when_no_config(tmp_path: Path) -> None:
    assert resolve_model(None, tmp_path / "missing.toml") == DEFAULT_MODEL


def test_invalid_config_model_type_errors(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("[ai_commit]\nmodel = 123\n")

    with pytest.raises(ConfigError, match="must be a string"):
        resolve_model(None, config_path)
