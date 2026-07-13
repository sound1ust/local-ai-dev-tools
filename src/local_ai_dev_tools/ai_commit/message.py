"""Commit-message validation and normalization."""

import re

SUBJECT_RE = re.compile(r"^(?:(?P<task>[A-Z]+-[0-9]+) )?(?P<subject>\S.*)$")


class CommitMessageError(ValueError):
    """Raised when generated commit text violates the required format."""


def build_attribution(model: str) -> str:
    """Return the required attribution paragraph for a model."""
    return f"Commit by {model}."


def normalize_model_output(output: str, model: str) -> str:
    """Normalize safe formatting issues from model output."""
    attribution = build_attribution(model)
    message = output.strip()
    if message.startswith("```"):
        lines = message.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        message = "\n".join(lines).strip()

    if not message:
        return ""

    lines = message.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and _is_attribution_line(lines[-1].strip()):
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()

    body = "\n".join(lines).rstrip()
    if not body:
        return attribution
    return f"{body}\n\n{attribution}"


def validate_commit_message(
    message: str,
    expected_task_key: str | None,
    model: str,
) -> str:
    """Validate important invariants and return normalized commit text."""
    attribution = build_attribution(model)
    normalized = normalize_model_output(message, model)
    if not normalized:
        raise CommitMessageError("commit message cannot be empty")

    lines = normalized.splitlines()
    if len(lines) < 3:
        raise CommitMessageError("commit message must include subject and attribution")

    subject_match = SUBJECT_RE.fullmatch(lines[0])
    if subject_match is None:
        raise CommitMessageError("commit subject is missing or malformed")

    task_key = subject_match.group("task")
    if expected_task_key is not None and task_key != expected_task_key:
        raise CommitMessageError(f"commit subject must start with {expected_task_key}")
    if expected_task_key is None and task_key is not None:
        raise CommitMessageError("commit subject must not start with a task key")

    if lines[-2] != "" or lines[-1] != attribution:
        raise CommitMessageError(
            f"commit message must end with a blank line and {attribution!r}"
        )

    return normalized


def _is_attribution_line(line: str) -> bool:
    return line.startswith("Commit by ") and line.endswith(".")
