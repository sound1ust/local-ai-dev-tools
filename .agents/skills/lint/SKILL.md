---
name: lint
description: Use when fixing Ruff lint failures, applying safe lint fixes, or checking Python style in this repo.
---

# Lint Skill

Use this skill when changing Python code, tests, docs that affect examples, or
project workflow files in this repository.

## Commands

- Run `task lint` for Ruff checks with safe fixes.
- Run `task typecheck` separately for ty checks.

`task lint` runs `uv run ruff check --fix src tests`.
`task typecheck` runs `uv run ty check`.

## Repo Rules

- Ruff line length is 88, as configured in `pyproject.toml`.
- Keep imports sorted by Ruff.
- Do not run formatter, linter, or type-checker commands outside the Taskfile
  workflow unless diagnosing a specific failure.
