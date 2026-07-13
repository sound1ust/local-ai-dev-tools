import argparse
import subprocess
from pathlib import Path

from local_ai_dev_tools.ai_commit.cli import EXIT_OK, run
from local_ai_dev_tools.ai_commit.git import GitClient

VALID_MESSAGE = """Add ai commit helper

- create typed cli modules;
- validate model output.

Commit by qwen2.5-coder:14b."""


def static_generate(prompt: str, model: str) -> str:
    return VALID_MESSAGE


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout


def init_repo(repo: Path) -> None:
    git(repo, "init")
    git(repo, "config", "user.email", "codex@example.com")
    git(repo, "config", "user.name", "Codex")
    (repo / "tracked.txt").write_text("base\n")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-m", "Initial commit")


def cli_args(*values: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task")
    parser.add_argument("--model")
    parser.add_argument("--message-only", action="store_true")
    parser.add_argument("--push", action="store_true")
    return parser.parse_args(list(values))


def test_fails_when_no_staged_changes_exist(tmp_path: Path) -> None:
    init_repo(tmp_path)
    code = run(
        args=cli_args(),
        git_client=GitClient(tmp_path),
        generate_message=static_generate,
        config_path=tmp_path / "missing.toml",
    )

    assert code != EXIT_OK
    assert git(tmp_path, "rev-list", "--count", "HEAD").strip() == "1"


def test_commits_staged_changes_only_and_leaves_other_files(tmp_path: Path) -> None:
    init_repo(tmp_path)
    (tmp_path / "tracked.txt").write_text("staged\n")
    git(tmp_path, "add", "tracked.txt")
    (tmp_path / "tracked.txt").write_text("unstaged\n")
    (tmp_path / "untracked.txt").write_text("untracked\n")

    code = run(
        args=cli_args(),
        git_client=GitClient(tmp_path),
        generate_message=static_generate,
        config_path=tmp_path / "missing.toml",
    )

    assert code == EXIT_OK
    assert git(tmp_path, "show", "HEAD:tracked.txt") == "staged\n"
    assert (tmp_path / "tracked.txt").read_text() == "unstaged\n"
    assert (tmp_path / "untracked.txt").read_text() == "untracked\n"


def test_message_only_does_not_create_commit(tmp_path: Path) -> None:
    init_repo(tmp_path)
    (tmp_path / "tracked.txt").write_text("staged\n")
    git(tmp_path, "add", "tracked.txt")

    code = run(
        args=cli_args("--message-only"),
        git_client=GitClient(tmp_path),
        generate_message=static_generate,
        config_path=tmp_path / "missing.toml",
    )

    assert code == EXIT_OK
    assert git(tmp_path, "rev-list", "--count", "HEAD").strip() == "1"


def test_status_prepares_model_friendly_diff(tmp_path: Path) -> None:
    init_repo(tmp_path)
    (tmp_path / "tracked.txt").write_text("staged\n")
    (tmp_path / "uv.lock").write_text('package = "noisy"\nhash = "abc"\n')
    git(tmp_path, "add", "tracked.txt", "uv.lock")

    status = GitClient(tmp_path).status()

    assert "Changed intent:" in status.staged_diff
    assert "Changed files:" in status.staged_diff
    assert "Selected implementation changes:" in status.staged_diff
    assert "staged" in status.staged_diff
    assert "uv.lock" in status.staged_diff
    assert 'package = "noisy"' not in status.staged_diff
    assert "lockfile diff omitted" in status.staged_diff


def test_status_reports_lockfile_only_changes(tmp_path: Path) -> None:
    init_repo(tmp_path)
    (tmp_path / "uv.lock").write_text('package = "noisy"\nhash = "abc"\n')
    git(tmp_path, "add", "uv.lock")

    status = GitClient(tmp_path).status()

    assert status.staged_diff.strip()
    assert "lockfile or generated changes" in status.staged_diff
    assert "uv.lock" in status.staged_diff
    assert 'package = "noisy"' not in status.staged_diff
    assert "lockfile diff omitted" in status.staged_diff
