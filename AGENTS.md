# Repository Instructions

This project is a public Python 3.14 `uv` package. The import root is
`local_ai_dev_tools`, and the first CLI entry point is `ai-commit`.

## Development

- Install dependencies with `uv sync --dev`.
- Use repo-local skills from `.agents/skills/` for focused workflows:
  - `lint` for Ruff and safe lint fixes;
  - `pytest-testing` for test layout, test edits, and pytest verification;
  - `typehints` for ty issues and typed API changes.
- Optional local hook setup: `uv run pre-commit install`.

Tests are organized by level under `tests/ai_commit/`:

- `tests/ai_commit/unit/` contains pure unit tests for CLI fakes, config
  resolution, message validation, Ollama wrapping, prompt construction, and
  task-key parsing.
- `tests/ai_commit/integration/` contains tests that create temporary Git repos
  and run real `git`.

## ai-commit Rules

- Use staged changes only; never auto-stage files.
- Report unstaged and untracked files as context.
- Keep Git operations as explicit subprocess argv calls to the installed `git`.
- Use the official `ollama` Python package directly for model calls.
- Resolve the Ollama model from `--model`, then
  `~/.config/local-ai-dev-tools/config.toml`, then the built-in default.
- Do not add remote-model fallback behavior.
- Preserve generic Git failure handling: surface commit and push errors directly.
