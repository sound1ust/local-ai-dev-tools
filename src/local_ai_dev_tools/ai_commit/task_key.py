"""Task-key parsing rules."""

import re

TASK_KEY_RE = re.compile(r"^[A-Z]+-[0-9]+$")
BRANCH_TASK_KEY_RE = re.compile(r"(?<![A-Z0-9])([A-Z]+-[0-9]+)(?![A-Z0-9])")


def validate_task_key(task_key: str) -> str:
    """Return a task key or raise ValueError when it is invalid."""
    if not TASK_KEY_RE.fullmatch(task_key):
        raise ValueError(f"invalid task key {task_key!r}; expected format like PD-10")
    return task_key


def extract_task_key_from_branch(branch_name: str) -> str | None:
    """Extract the first valid uppercase task key from a branch name."""
    match = BRANCH_TASK_KEY_RE.search(branch_name)
    if match is None:
        return None
    return match.group(1)


def resolve_task_key(explicit_task: str | None, branch_name: str) -> str | None:
    """Apply task-key precedence rules."""
    if explicit_task is not None:
        return validate_task_key(explicit_task)
    return extract_task_key_from_branch(branch_name)

