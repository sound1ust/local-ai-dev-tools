import pytest

from local_ai_dev_tools.ai_commit.task_key import (
    extract_task_key_from_branch,
    resolve_task_key,
    validate_task_key,
)


@pytest.mark.parametrize("task_key", ["PD-10", "ABC-123"])
def test_validate_task_key_accepts_valid_key(task_key: str) -> None:
    assert validate_task_key(task_key) == task_key


@pytest.mark.parametrize("task_key", ["pd-10", "PD10", "PD-", "PD-abc", "PD-10-extra"])
def test_validate_task_key_rejects_invalid_key(task_key: str) -> None:
    with pytest.raises(ValueError):
        validate_task_key(task_key)


@pytest.mark.parametrize(
    ("branch_name", "expected"),
    [
        ("feature/PD-10-ai-commit", "PD-10"),
        ("PD-10", "PD-10"),
        ("feature/no-ticket", None),
        ("feature/pd-10-lowercase", None),
    ],
)
def test_extract_task_key_from_branch(branch_name: str, expected: str | None) -> None:
    assert extract_task_key_from_branch(branch_name) == expected


def test_explicit_task_key_wins_over_branch() -> None:
    assert resolve_task_key("PD-10", "feature/AA-1") == "PD-10"


def test_no_prefix_behavior_without_valid_task_key() -> None:
    assert resolve_task_key(None, "feature/local-work") is None

