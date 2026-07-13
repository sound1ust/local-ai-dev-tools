"""Explicit subprocess wrappers for Git operations."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from local_ai_dev_tools.ai_commit.diff import (
    MAX_FILE_PATCH_CHARS,
    prepare_staged_diff,
)

_DIFF_TRUNCATED_MARKER = "\n[diff output truncated by ai-commit]\n"


class GitError(RuntimeError):
    """Raised when a Git command fails."""


@dataclass(frozen=True)
class GitStatus:
    branch_name: str
    staged_diff: str
    unstaged_files: tuple[str, ...]
    untracked_files: tuple[str, ...]


class GitClient:
    """Git subprocess boundary."""

    def __init__(self, cwd: Path | None = None) -> None:
        self._cwd = cwd

    def status(self) -> GitStatus:
        branch_name = self._run(["git", "branch", "--show-current"]).stdout.strip()
        stat = self._run(["git", "diff", "--cached", "--stat"]).stdout
        name_status = self._run(["git", "diff", "--cached", "--name-status"]).stdout
        raw_diff = self._staged_prompt_diff(name_status)
        prepared_diff = prepare_staged_diff(
            stat=stat,
            name_status=name_status,
            raw_diff=raw_diff,
        )
        porcelain = self._run(["git", "status", "--porcelain=v1"]).stdout
        unstaged_files, untracked_files = _parse_porcelain_status(porcelain)
        return GitStatus(
            branch_name=branch_name,
            staged_diff=prepared_diff.text,
            unstaged_files=unstaged_files,
            untracked_files=untracked_files,
        )

    def commit(self, message: str) -> None:
        self._run(["git", "commit", "-F", "-"], input_text=message)

    def push(self) -> None:
        self._run(["git", "push"])

    def _run(
        self,
        argv: list[str],
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                argv,
                cwd=self._cwd,
                input=input_text,
                text=True,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            joined = " ".join(argv)
            if detail:
                raise GitError(f"{joined} failed: {detail}") from exc
            raise GitError(f"{joined} failed with exit code {exc.returncode}") from exc

    def _staged_prompt_diff(self, name_status: str) -> str:
        patches: list[str] = []
        for path in _paths_requiring_patch(name_status):
            if _is_noisy_path(path):
                continue
            patches.append(
                self._run_stdout_limited(
                    ["git", "diff", "--cached", "--no-ext-diff", "--", path],
                    max_bytes=MAX_FILE_PATCH_CHARS + len(_DIFF_TRUNCATED_MARKER),
                )
            )
        return "\n".join(patch for patch in patches if patch.strip())

    def _run_stdout_limited(self, argv: list[str], *, max_bytes: int) -> str:
        process = subprocess.Popen(
            argv,
            cwd=self._cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if process.stdout is None:
            raise GitError(f"{' '.join(argv)} failed to open stdout")

        chunks: list[bytes] = []
        captured = 0
        truncated = False
        while captured <= max_bytes:
            chunk = process.stdout.read(min(8192, max_bytes + 1 - captured))
            if not chunk:
                break
            chunks.append(chunk)
            captured += len(chunk)
            if captured > max_bytes:
                truncated = True
                process.kill()
                break

        stderr = process.stderr.read() if process.stderr is not None else b""
        returncode = process.wait()
        if returncode != 0 and not truncated:
            detail = stderr.decode(errors="replace").strip()
            joined = " ".join(argv)
            if detail:
                raise GitError(f"{joined} failed: {detail}")
            raise GitError(f"{joined} failed with exit code {returncode}")

        output = b"".join(chunks)[:max_bytes].decode(errors="replace")
        if truncated:
            return f"{output}{_DIFF_TRUNCATED_MARKER}"
        return output


def _parse_porcelain_status(porcelain: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    unstaged: list[str] = []
    untracked: list[str] = []
    for line in porcelain.splitlines():
        if line.startswith("?? "):
            untracked.append(line[3:])
            continue
        if len(line) >= 4 and line[1] != " ":
            unstaged.append(line[3:])
    return tuple(unstaged), tuple(untracked)


def _paths_requiring_patch(name_status: str) -> tuple[str, ...]:
    paths: list[str] = []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        paths.append(parts[-1])
    return tuple(paths)


def _is_noisy_path(path: str) -> bool:
    return Path(path).name in {
        "uv.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
    } or path.endswith(".lock")
