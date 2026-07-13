import argparse
from io import StringIO
from pathlib import Path

from local_ai_dev_tools.ai_commit.cli import (
    EXIT_GENERATION_FAILED,
    EXIT_GIT_FAILED,
    EXIT_INVALID_MESSAGE,
    EXIT_NO_STAGED_CHANGES,
    EXIT_OK,
    EXIT_PUSH_FAILED,
    EXIT_USAGE,
    build_parser,
    run,
)
from local_ai_dev_tools.ai_commit.git import GitError, GitStatus
from local_ai_dev_tools.ai_commit.ollama import OllamaError

DEFAULT_MODEL = "gemma4:cloud"
VALID_MESSAGE = """PD-10 Add ai commit helper

- create typed cli modules;
- validate model output.

Commit by gemma4:cloud."""


class FakeGit:
    def __init__(self, status: GitStatus) -> None:
        self.status_value = status
        self.commits: list[str] = []
        self.pushes = 0
        self.fail_commit = False
        self.fail_push = False

    def status(self) -> GitStatus:
        return self.status_value

    def commit(self, message: str) -> None:
        if self.fail_commit:
            raise GitError("commit failed")
        self.commits.append(message)

    def push(self) -> None:
        if self.fail_push:
            raise GitError("push failed")
        self.pushes += 1


class FakeGenerator:
    def __init__(self, message: str = VALID_MESSAGE) -> None:
        self.message = message
        self.prompts: list[str] = []
        self.models: list[str] = []
        self.fail = False

    def __call__(self, prompt: str, model: str) -> str:
        if self.fail:
            raise OllamaError("ollama failed")
        self.prompts.append(prompt)
        self.models.append(model)
        return self.message


def args(*values: str) -> argparse.Namespace:
    return build_parser().parse_args(list(values))


def staged_status(branch_name: str = "feature/PD-10-work") -> GitStatus:
    return GitStatus(
        branch_name=branch_name,
        staged_diff="diff --git a/file.txt b/file.txt\n+hello",
        unstaged_files=(),
        untracked_files=(),
    )


def test_parser_argument_combinations() -> None:
    parsed = args(
        "--task",
        "PD-10",
        "--model",
        "custom-model",
        "--message-only",
        "--push",
    )

    assert parsed.task == "PD-10"
    assert parsed.model == "custom-model"
    assert parsed.message_only is True
    assert parsed.push is True


def test_message_only_prints_without_committing(tmp_path: Path) -> None:
    git = FakeGit(staged_status())
    generate = FakeGenerator()
    stdout = StringIO()

    code = run(
        args=args("--message-only"),
        git_client=git,
        generate_message=generate,
        config_path=tmp_path / "missing.toml",
        stdout=stdout,
    )

    assert code == EXIT_OK
    assert stdout.getvalue().strip() == VALID_MESSAGE
    assert git.commits == []
    assert generate.models == [DEFAULT_MODEL]


def test_invalid_task_key_returns_usage_error(tmp_path: Path) -> None:
    stderr = StringIO()

    code = run(
        args=args("--task", "pd-10"),
        git_client=FakeGit(staged_status()),
        generate_message=FakeGenerator(),
        config_path=tmp_path / "missing.toml",
        stderr=stderr,
    )

    assert code == EXIT_USAGE
    assert "invalid task key" in stderr.getvalue()


def test_no_staged_changes_returns_nonzero(tmp_path: Path) -> None:
    status = GitStatus("feature/PD-10-work", "", (), ())
    stderr = StringIO()

    code = run(
        args=args(),
        git_client=FakeGit(status),
        generate_message=FakeGenerator(),
        config_path=tmp_path / "missing.toml",
        stderr=stderr,
    )

    assert code == EXIT_NO_STAGED_CHANGES
    assert "no staged changes" in stderr.getvalue()


def test_ollama_failure_returns_nonzero(tmp_path: Path) -> None:
    generate = FakeGenerator()
    generate.fail = True

    assert (
        run(
            args=args(),
            git_client=FakeGit(staged_status()),
            generate_message=generate,
            config_path=tmp_path / "missing.toml",
        )
        == EXIT_GENERATION_FAILED
    )


def test_invalid_model_output_returns_nonzero(tmp_path: Path) -> None:
    generate = FakeGenerator("")

    assert (
        run(
            args=args(),
            git_client=FakeGit(staged_status()),
            generate_message=generate,
            config_path=tmp_path / "missing.toml",
        )
        == EXIT_INVALID_MESSAGE
    )


def test_generated_prompt_is_passed_with_resolved_cli_model(tmp_path: Path) -> None:
    git = FakeGit(staged_status())
    generate = FakeGenerator()

    code = run(
        args=args("--model", "cli-model"),
        git_client=git,
        generate_message=generate,
        config_path=tmp_path / "missing.toml",
    )

    assert code == EXIT_OK
    assert generate.models == ["cli-model"]
    assert "diff --git a/file.txt b/file.txt" in generate.prompts[0]


def test_push_runs_only_after_successful_commit(tmp_path: Path) -> None:
    git = FakeGit(staged_status())

    code = run(
        args=args("--push"),
        git_client=git,
        generate_message=FakeGenerator(),
        config_path=tmp_path / "missing.toml",
    )

    assert code == EXIT_OK
    assert len(git.commits) == 1
    assert git.pushes == 1


def test_push_does_not_run_after_commit_failure(tmp_path: Path) -> None:
    git = FakeGit(staged_status())
    git.fail_commit = True

    stderr = StringIO()

    code = run(
        args=args("--push"),
        git_client=git,
        generate_message=FakeGenerator(),
        config_path=tmp_path / "missing.toml",
        stderr=stderr,
    )

    assert code == EXIT_GIT_FAILED
    assert git.pushes == 0
    assert "commit failed" in stderr.getvalue()


def test_push_failure_returns_nonzero(tmp_path: Path) -> None:
    git = FakeGit(staged_status())
    git.fail_push = True

    stderr = StringIO()

    code = run(
        args=args("--push"),
        git_client=git,
        generate_message=FakeGenerator(),
        config_path=tmp_path / "missing.toml",
        stderr=stderr,
    )

    assert code == EXIT_PUSH_FAILED
    assert "push failed" in stderr.getvalue()


def test_reports_unstaged_and_untracked_context(tmp_path: Path) -> None:
    status = GitStatus(
        branch_name="feature/PD-10-work",
        staged_diff="diff",
        unstaged_files=("modified.txt",),
        untracked_files=("new.txt",),
    )
    stderr = StringIO()

    code = run(
        args=args(),
        git_client=FakeGit(status),
        generate_message=FakeGenerator(),
        config_path=tmp_path / "missing.toml",
        stderr=stderr,
    )

    assert code == EXIT_OK
    assert "modified.txt" in stderr.getvalue()
    assert "new.txt" in stderr.getvalue()
    assert "  new.txt\n\nai-commit: committed staged changes" in stderr.getvalue()
