from local_ai_dev_tools.ai_commit.prompt import build_commit_prompt


def test_prompt_includes_staged_diff_and_format_rules() -> None:
    prompt = build_commit_prompt(
        "diff --git a/a.txt b/a.txt\n+hello",
        "PD-10",
        "Commit by qwen2.5-coder:14b.",
    )

    assert "diff --git a/a.txt b/a.txt" in prompt
    assert "Start the subject with exactly 'PD-10 '" in prompt
    assert "Use an imperative subject." in prompt
    assert "lowercase action bullets" in prompt
    assert "Commit by qwen2.5-coder:14b." in prompt


def test_prompt_includes_no_prefix_rule() -> None:
    prompt = build_commit_prompt("diff", None, "Commit by qwen2.5-coder:14b.")

    assert "Do not include a task-key prefix." in prompt
