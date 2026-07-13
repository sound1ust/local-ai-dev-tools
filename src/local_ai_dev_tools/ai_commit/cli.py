"""Command-line entry point for ai-commit."""

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol, TextIO

from local_ai_dev_tools.ai_commit.config import (
    DEFAULT_CONFIG_PATH,
    ConfigError,
    resolve_model,
)
from local_ai_dev_tools.ai_commit.git import GitClient, GitError, GitStatus
from local_ai_dev_tools.ai_commit.message import (
    CommitMessageError,
    build_attribution,
    validate_commit_message,
)
from local_ai_dev_tools.ai_commit.ollama import OllamaError, generate_commit_message
from local_ai_dev_tools.ai_commit.prompt import build_commit_prompt
from local_ai_dev_tools.ai_commit.task_key import resolve_task_key

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_STAGED_CHANGES = 3
EXIT_GENERATION_FAILED = 4
EXIT_INVALID_MESSAGE = 5
EXIT_GIT_FAILED = 6
EXIT_PUSH_FAILED = 7


class GitOperations(Protocol):
    def status(self) -> GitStatus: ...

    def commit(self, message: str) -> None: ...

    def push(self) -> None: ...


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-commit",
        description="Generate a local Ollama commit message for staged changes.",
    )
    parser.add_argument("--task", help="explicit task key, for example PD-10")
    parser.add_argument("--model", help="Ollama model name to use for this run")
    parser.add_argument(
        "--message-only",
        action="store_true",
        help="print the generated message without committing",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="push after a successful commit",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args=args)


def run(
    *,
    args: argparse.Namespace,
    git_client: GitOperations | None = None,
    generate_message: Callable[[str, str], str] | None = None,
    config_path: Path = DEFAULT_CONFIG_PATH,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    git = git_client or GitClient()
    generate = generate_message or generate_commit_message

    try:
        model = resolve_model(args.model, config_path)
        status = git.status()
        task_key = resolve_task_key(args.task, status.branch_name)
    except ConfigError as exc:
        print(f"ai-commit: {exc}", file=stderr)
        return EXIT_USAGE
    except ValueError as exc:
        print(f"ai-commit: {exc}", file=stderr)
        return EXIT_USAGE
    except GitError as exc:
        print(f"ai-commit: {exc}", file=stderr)
        return EXIT_GIT_FAILED

    _print_context(status.unstaged_files, status.untracked_files, stderr=stderr)

    if not status.staged_diff.strip():
        print(
            "ai-commit: no staged changes; stage files before running ai-commit",
            file=stderr,
        )
        return EXIT_NO_STAGED_CHANGES

    attribution = build_attribution(model)
    prompt = build_commit_prompt(status.staged_diff, task_key, attribution)
    try:
        raw_message = generate(prompt, model)
    except OllamaError as exc:
        print(f"ai-commit: {exc}", file=stderr)
        return EXIT_GENERATION_FAILED

    try:
        message = validate_commit_message(raw_message, task_key, model)
    except CommitMessageError as exc:
        print(f"ai-commit: invalid model output: {exc}", file=stderr)
        return EXIT_INVALID_MESSAGE

    if args.message_only:
        print(message, file=stdout)
        return EXIT_OK

    try:
        git.commit(message)
    except GitError as exc:
        print(f"ai-commit: commit failed: {exc}", file=stderr)
        return EXIT_GIT_FAILED

    print("ai-commit: committed staged changes", file=stderr)

    if args.push:
        try:
            git.push()
        except GitError as exc:
            print(f"ai-commit: push failed: {exc}", file=stderr)
            return EXIT_PUSH_FAILED
        print("ai-commit: pushed commit", file=stderr)

    return EXIT_OK


def _print_context(
    unstaged_files: tuple[str, ...],
    untracked_files: tuple[str, ...],
    *,
    stderr: TextIO,
) -> None:
    printed_context = False
    if unstaged_files:
        print("ai-commit: unstaged files present:", file=stderr)
        for path in unstaged_files:
            print(f"  {path}", file=stderr)
        printed_context = True
    if untracked_files:
        print("ai-commit: untracked files present:", file=stderr)
        for path in untracked_files:
            print(f"  {path}", file=stderr)
        printed_context = True
    if printed_context:
        print(file=stderr)

if __name__ == "__main__":
    raise SystemExit(main())
