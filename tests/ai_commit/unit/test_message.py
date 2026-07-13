import pytest

from local_ai_dev_tools.ai_commit.message import (
    CommitMessageError,
    build_attribution,
    normalize_model_output,
    validate_commit_message,
)

MODEL = "qwen2.5-coder:14b"
ATTRIBUTION = build_attribution(MODEL)
VALID_MESSAGE = f"""PD-10 Add ai commit helper

- create typed cli modules;
- validate model output.

{ATTRIBUTION}"""


def test_validate_commit_message_accepts_required_format() -> None:
    assert validate_commit_message(VALID_MESSAGE, "PD-10", MODEL) == VALID_MESSAGE


def test_validate_commit_message_accepts_no_prefix_when_expected() -> None:
    message = f"""Add ai commit helper

- create typed cli modules;
- validate model output.

{ATTRIBUTION}"""

    assert validate_commit_message(message, None, MODEL) == message


def test_validate_commit_message_accepts_non_allowlisted_subject() -> None:
    message = f"""Document ai commit behavior

Body text.

{ATTRIBUTION}"""

    assert validate_commit_message(message, None, MODEL) == message


def test_validate_commit_message_accepts_lighter_body_formatting() -> None:
    message = f"""PD-10 Add ai commit helper

Body line without bullets
Another Line Without Required Punctuation

{ATTRIBUTION}"""

    assert validate_commit_message(message, "PD-10", MODEL) == message


def test_normalize_model_output_strips_code_fence() -> None:
    assert (
        normalize_model_output(f"```text\n{VALID_MESSAGE}\n```", MODEL)
        == VALID_MESSAGE
    )


def test_normalize_model_output_appends_missing_attribution() -> None:
    message = """Add ai commit helper

Body text."""

    assert normalize_model_output(message, MODEL) == f"{message}\n\n{ATTRIBUTION}"


def test_normalize_model_output_ensures_one_blank_line_before_attribution() -> None:
    message = f"""Add ai commit helper


{ATTRIBUTION}"""

    assert (
        normalize_model_output(message, MODEL)
        == f"Add ai commit helper\n\n{ATTRIBUTION}"
    )


def test_normalize_model_output_replaces_generic_attribution() -> None:
    message = """Add ai commit helper

Commit by old-model."""

    assert (
        normalize_model_output(message, MODEL)
        == f"Add ai commit helper\n\n{ATTRIBUTION}"
    )


def test_validate_commit_message_rejects_empty_output() -> None:
    with pytest.raises(CommitMessageError, match="empty"):
        validate_commit_message("", None, MODEL)


def test_validate_commit_message_rejects_missing_task_prefix_when_expected() -> None:
    with pytest.raises(CommitMessageError, match="PD-10"):
        validate_commit_message(
            f"Add ai commit helper\n\n{ATTRIBUTION}",
            "PD-10",
            MODEL,
        )


def test_validate_commit_message_rejects_wrong_task_prefix_when_expected() -> None:
    with pytest.raises(CommitMessageError, match="PD-10"):
        validate_commit_message(
            f"AA-1 Add ai commit helper\n\n{ATTRIBUTION}",
            "PD-10",
            MODEL,
        )


def test_validate_commit_message_rejects_unexpected_task_prefix() -> None:
    with pytest.raises(CommitMessageError, match="must not start"):
        validate_commit_message(
            f"PD-10 Add ai commit helper\n\n{ATTRIBUTION}",
            None,
            MODEL,
        )
