# local-ai-dev-tools

Local AI-powered developer tools for day-to-day development workflows.

## Install

This project uses Python 3.14, `uv`, and [Task](https://taskfile.dev/).

```sh
uv sync --dev
uv tool install --editable .
```

The first CLI is `ai-commit`, an Ollama-powered commit helper. It requires
Ollama to be installed and the server to be running (`ollama serve`).

The built-in default model is `gemma4:cloud`, which is Ollama's cloud-backed
model path. That means staged diff content is sent through Ollama Cloud unless
you override the model. For local-only use, configure or pass a local Ollama
model such as `qwen2.5-coder:14b`. The tool never falls back to another remote
model on its own.

Override the model for one run:

```sh
ai-commit --model qwen2.5-coder:14b
```

Or configure it globally in `~/.config/local-ai-dev-tools/config.toml`:

```toml
[ai_commit]
model = "gemma4:cloud"
```

## Usage

Stage the changes you want to commit, then run:

```sh
ai-commit
ai-commit --task PD-10
ai-commit --message-only
ai-commit --model gemma4:cloud
ai-commit --push
ai-commit --task PD-10 --push
```

`ai-commit` uses staged changes only and never stages files for you. Unstaged and
untracked files are reported as context. If no explicit task key is passed, the
tool extracts a valid key from the current branch name. If no valid key exists,
the commit message is generated without a task prefix.

The expected message format is:

```text
PD-10 Imperative subject

- lowercase action bullet;
- lowercase final bullet.

Commit by gemma4:cloud.
```

## Quality

```sh
task lint
task typecheck
task test
```

`task lint` runs Ruff with safe fixes. `task typecheck` runs ty. `task test`
runs pytest.
