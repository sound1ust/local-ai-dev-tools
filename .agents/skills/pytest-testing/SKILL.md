---
name: pytest-testing
description: Use when adding, moving, or refactoring pytest tests in this repo.
---

# Pytest Testing Skill

Use this skill when adding, moving, or changing tests in this repository.

## Commands

- Run `task test` for the full test suite.
- After changing the test layout, run
  `uv run python -m pytest tests/ai_commit/unit tests/ai_commit/integration`
  once to verify direct discovery from the nested layout.

## Test Layout

- `tests/ai_commit/unit/` contains pure unit tests:
  - CLI argument and flow tests with fakes;
  - config resolution;
  - message normalization and validation;
  - Ollama call wrapper behavior;
  - prompt construction;
  - task-key parsing.
- `tests/ai_commit/integration/` contains tests that create temporary Git repos
  and run real `git`.

Keep temporary Git repository tests in `tests/ai_commit/integration/`.
