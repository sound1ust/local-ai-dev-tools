"""Prepare staged Git changes for local model prompts."""

from dataclasses import dataclass
from pathlib import PurePosixPath

MAX_FILE_PATCH_CHARS = 8_000
MAX_PREPARED_DIFF_CHARS = 24_000

_NOISY_FILENAMES = {
    "uv.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
}


@dataclass(frozen=True)
class PreparedDiff:
    """Model-facing staged change summary."""

    text: str
    has_changes: bool


@dataclass(frozen=True)
class _Patch:
    path: str
    text: str
    category: str


@dataclass
class _PreparedParts:
    selected: list[str]
    summarized_tests: list[str]
    omitted: list[str]


def prepare_staged_diff(
    *,
    stat: str,
    name_status: str,
    raw_diff: str,
    max_file_patch_chars: int = MAX_FILE_PATCH_CHARS,
    max_total_chars: int = MAX_PREPARED_DIFF_CHARS,
) -> PreparedDiff:
    """Convert raw staged Git output into a compact model-facing diff."""
    if not raw_diff.strip() and not name_status.strip():
        return PreparedDiff(text="", has_changes=False)

    implementation_patches: list[_Patch] = []
    test_patches: list[_Patch] = []
    summarized_tests: list[str] = []
    omitted: list[str] = [
        f"- {path}: lockfile diff omitted" for path in _noisy_paths_from_name_status(
            name_status
        )
    ]

    for patch in _split_file_patches(raw_diff):
        path = _path_from_patch(patch)
        if path is None:
            continue
        if _is_noisy_path(path):
            omission = f"- {path}: lockfile diff omitted"
            if omission not in omitted:
                omitted.append(omission)
            continue
        category = _category_for_path(path)
        parsed = _Patch(path=path, text=patch.strip(), category=category)
        if category == "tests":
            test_patches.append(parsed)
        else:
            implementation_patches.append(parsed)

    include_tests = not implementation_patches
    implementation_patches.sort(key=_patch_order)
    selected_patches = implementation_patches + (test_patches if include_tests else [])
    if not include_tests:
        summarized_tests.extend(_summarize_patch(patch) for patch in test_patches)

    sections: list[str] = [
        "Changed intent:",
        *_intent_lines(name_status),
        "",
        "Changed files:",
        name_status.strip() or "(none)",
        "",
        "Staged stat:",
        stat.strip() or "(none)",
    ]

    parts = _fit_optional_sections(
        base_sections=sections,
        selected_patches=selected_patches,
        summarized_tests=summarized_tests,
        omitted=omitted,
        max_file_patch_chars=max_file_patch_chars,
        max_total_chars=max_total_chars,
    )

    if parts.selected:
        sections.extend(
            ["", "Selected implementation changes:", "\n\n".join(parts.selected)]
        )
    if parts.summarized_tests:
        sections.extend(
            ["", "Summarized test changes:", "\n".join(parts.summarized_tests)]
        )
    if parts.omitted:
        sections.extend(["", "Omitted:", "\n".join(parts.omitted)])

    text = "\n".join(sections).strip() + "\n"
    return PreparedDiff(text=text, has_changes=True)


def _fit_optional_sections(
    *,
    base_sections: list[str],
    selected_patches: list[_Patch],
    summarized_tests: list[str],
    omitted: list[str],
    max_file_patch_chars: int,
    max_total_chars: int,
) -> _PreparedParts:
    selected: list[str] = []
    kept_summaries: list[str] = []
    kept_omitted: list[str] = []
    pending_omitted = list(omitted)
    for patch in selected_patches:
        if len(patch.text) > max_file_patch_chars:
            pending_omitted.append(
                f"- {patch.path}: large diff omitted ({len(patch.text)} characters)"
            )
            continue
        selected_text = f"File: {patch.path}\n{patch.text}"
        candidate = _render_sections(
            base_sections,
            [*selected, selected_text],
            kept_summaries,
            kept_omitted,
        )
        if len(candidate) > max_total_chars:
            pending_omitted.append(
                f"- {patch.path}: omitted to keep prompt under size limit"
            )
            continue

        selected.append(selected_text)

    for summary in summarized_tests:
        candidate = _render_sections(
            base_sections,
            selected,
            [*kept_summaries, summary],
            kept_omitted,
        )
        if len(candidate) > max_total_chars:
            pending_omitted.append(
                "- additional test summaries omitted to keep prompt under size limit"
            )
            break
        kept_summaries.append(summary)

    for omission in pending_omitted:
        candidate = _render_sections(
            base_sections,
            selected,
            kept_summaries,
            [*kept_omitted, omission],
        )
        if len(candidate) > max_total_chars:
            remaining = len(pending_omitted) - len(kept_omitted)
            summary = (
                f"- {remaining} additional files omitted "
                "to keep prompt under size limit"
            )
            if _fits_omitted_summary(
                base_sections,
                selected,
                kept_summaries,
                kept_omitted,
                summary,
                max_total_chars,
            ):
                kept_omitted.append(summary)
            elif not kept_omitted:
                fallback = "- omitted details exceed prompt size limit"
                if _fits_omitted_summary(
                    base_sections,
                    selected,
                    kept_summaries,
                    kept_omitted,
                    fallback,
                    max_total_chars,
                ):
                    kept_omitted.append(fallback)
            break
        kept_omitted.append(omission)

    return _PreparedParts(
        selected=selected,
        summarized_tests=kept_summaries,
        omitted=kept_omitted,
    )


def _render_sections(
    base_sections: list[str],
    selected: list[str],
    summarized_tests: list[str],
    omitted: list[str],
) -> str:
    sections = list(base_sections)
    if selected:
        sections.extend(["", "Selected implementation changes:", "\n\n".join(selected)])
    if summarized_tests:
        sections.extend(["", "Summarized test changes:", "\n".join(summarized_tests)])
    if omitted:
        sections.extend(["", "Omitted:", "\n".join(omitted)])
    return "\n".join(sections).strip() + "\n"


def _fits_omitted_summary(
    base_sections: list[str],
    selected: list[str],
    summarized_tests: list[str],
    kept_omitted: list[str],
    summary: str,
    max_total_chars: int,
) -> bool:
    return (
        len(
            _render_sections(
                base_sections,
                selected,
                summarized_tests,
                [*kept_omitted, summary],
            )
        )
        <= max_total_chars
    )


def _split_file_patches(raw_diff: str) -> list[str]:
    patches: list[str] = []
    current: list[str] = []
    for line in raw_diff.splitlines():
        if line.startswith("diff --git ") and current:
            patches.append("\n".join(current))
            current = []
        current.append(line)
    if current:
        patches.append("\n".join(current))
    return patches


def _path_from_patch(patch: str) -> str | None:
    first_line = patch.splitlines()[0] if patch else ""
    parts = first_line.split()
    if len(parts) < 4 or parts[0:2] != ["diff", "--git"]:
        return None
    raw_path = parts[3]
    if raw_path.startswith("b/"):
        return raw_path[2:]
    return raw_path


def _is_noisy_path(path: str) -> bool:
    parsed = PurePosixPath(path)
    if parsed.name in _NOISY_FILENAMES:
        return True
    return parsed.suffix == ".lock"


def _category_for_path(path: str) -> str:
    parsed = PurePosixPath(path)
    parts = set(parsed.parts)
    if "tests" in parts or parsed.name.startswith("test_"):
        return "tests"
    if parsed.suffix == ".py" and "src" in parts:
        return "source"
    if parsed.suffix in {".toml", ".yaml", ".yml", ".json", ".ini", ".cfg"}:
        return "config"
    if parsed.suffix in {".md", ".rst", ".txt"}:
        return "docs"
    return "implementation"


def _patch_order(patch: _Patch) -> int:
    order = {
        "source": 0,
        "config": 1,
        "docs": 2,
        "implementation": 3,
    }
    return order.get(patch.category, 4)


def _intent_lines(name_status: str) -> list[str]:
    categories: dict[str, int] = {}
    for line in name_status.splitlines():
        path = _path_from_name_status(line)
        if path is None or _is_noisy_path(path):
            category = "lockfiles/generated"
        else:
            category = _category_for_path(path)
        categories[category] = categories.get(category, 0) + 1

    if not categories:
        return ["- staged file changes"]

    order = [
        "source",
        "config",
        "docs",
        "implementation",
        "tests",
        "lockfiles/generated",
    ]
    labels = {
        "source": "source code changes",
        "config": "configuration changes",
        "docs": "documentation changes",
        "implementation": "implementation changes",
        "tests": "test changes",
        "lockfiles/generated": "lockfile or generated changes",
    }
    return [
        f"- {labels[category]} ({categories[category]} file"
        f"{'' if categories[category] == 1 else 's'})"
        for category in order
        if category in categories
    ]


def _path_from_name_status(line: str) -> str | None:
    parts = line.split("\t")
    if len(parts) < 2:
        return None
    return parts[-1]


def _noisy_paths_from_name_status(name_status: str) -> list[str]:
    paths: list[str] = []
    for line in name_status.splitlines():
        path = _path_from_name_status(line)
        if path is not None and _is_noisy_path(path):
            paths.append(path)
    return paths


def _summarize_patch(patch: _Patch) -> str:
    additions = 0
    deletions = 0
    for line in patch.text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            additions += 1
        elif line.startswith("-"):
            deletions += 1
    return f"- {patch.path}: test diff summarized (+{additions}/-{deletions})"
