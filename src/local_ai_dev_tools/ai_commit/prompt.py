"""Prompt construction for local commit-message generation."""

COMMIT_PROMPT_TEMPLATE = (
    "You are writing a git commit message from staged changes only.\n"
    "\n"
    "Return only the commit message. Do not wrap it in code fences.\n"
    "\n"
    "Rules:\n"
    "- {prefix_rule}\n"
    "- Use an imperative subject.\n"
    "- Use lowercase action bullets in the body.\n"
    "- End every body bullet with a semicolon except the final bullet, "
    "which ends with a period.\n"
    "- End with this exact attribution paragraph:\n"
    "\n"
    "{attribution}\n"
    "\n"
    "Staged change digest:\n"
    "{staged_diff}\n"
)


def build_commit_prompt(
    staged_diff: str,
    task_key: str | None,
    attribution: str,
) -> str:
    """Create the deterministic prompt sent to Ollama."""
    prefix_rule = (
        f"Start the subject with exactly '{task_key} ' followed by the subject."
        if task_key is not None
        else "Do not include a task-key prefix."
    )
    return COMMIT_PROMPT_TEMPLATE.format(
        prefix_rule=prefix_rule,
        attribution=attribution,
        staged_diff=staged_diff,
    )
