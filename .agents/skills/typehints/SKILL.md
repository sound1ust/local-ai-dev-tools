---
name: typehints
description: Use when fixing ty type-checking failures, changing typed APIs, or tightening annotations in this Python repo.
---

# Type Hints Skill

Use this skill when changing Python APIs, function signatures, tests with fakes,
or typed helper code in this repository.

## Commands

- Run `task typecheck` to check types with ty.
- Run `task lint` separately for Ruff checks with safe fixes.

## Repo Rules

- The type checker is ty, invoked through `task typecheck`.
- Keep public and internal function signatures explicit.
- Prefer precise built-in collection types such as `list[str]` and
  `tuple[str, ...]`.
- Keep test fakes typed enough for ty to validate the exercised flow.
