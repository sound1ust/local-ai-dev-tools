"""Model configuration resolution for ai-commit."""

import tomllib
from pathlib import Path

DEFAULT_MODEL = "gemma4:cloud"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "local-ai-dev-tools" / "config.toml"


class ConfigError(RuntimeError):
    """Raised when model configuration cannot be loaded."""


def resolve_model(
    cli_model: str | None,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> str:
    """Resolve the Ollama model from CLI, global config, then built-in default."""
    if cli_model is not None and cli_model.strip():
        return cli_model.strip()

    config_model = _read_config_model(config_path)
    if config_model is not None:
        return config_model

    return DEFAULT_MODEL


def _read_config_model(config_path: Path) -> str | None:
    config = _read_config(config_path)
    if config is None:
        return None

    ai_commit = config.get("ai_commit")
    if not isinstance(ai_commit, dict):
        return None

    model = ai_commit.get("model")
    if model is None:
        return None
    if not isinstance(model, str):
        raise ConfigError(f"ai_commit.model in {config_path} must be a string")

    stripped = model.strip()
    return stripped or None


def _read_config(config_path: Path) -> dict[str, object] | None:
    if not config_path.exists():
        return None

    try:
        return tomllib.loads(config_path.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid config TOML at {config_path}: {exc}") from exc
