from local_ai_dev_tools.ai_commit.diff import prepare_staged_diff


def test_prepare_staged_diff_includes_source_before_summarized_tests() -> None:
    raw_diff = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1 @@
-print("old")
+print("new")
diff --git a/tests/test_app.py b/tests/test_app.py
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -1 +1 @@
-assert old()
+assert new()
"""

    prepared = prepare_staged_diff(
        stat=" src/app.py | 2 +-\n tests/test_app.py | 2 +-\n",
        name_status="M\tsrc/app.py\nM\ttests/test_app.py\n",
        raw_diff=raw_diff,
    )

    assert prepared.has_changes is True
    assert "Changed intent:" in prepared.text
    assert "Selected implementation changes:" in prepared.text
    assert "File: src/app.py" in prepared.text
    assert 'print("new")' in prepared.text
    assert "Summarized test changes:" in prepared.text
    assert "- tests/test_app.py: test diff summarized" in prepared.text
    assert "assert new()" not in prepared.text
    assert prepared.text.index("File: src/app.py") < prepared.text.index(
        "Summarized test changes:"
    )


def test_prepare_staged_diff_includes_tests_when_test_only() -> None:
    raw_diff = """diff --git a/tests/test_app.py b/tests/test_app.py
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -1 +1 @@
-assert old()
+assert new()
"""

    prepared = prepare_staged_diff(
        stat=" tests/test_app.py | 2 +-\n",
        name_status="M\ttests/test_app.py\n",
        raw_diff=raw_diff,
    )

    assert "Selected implementation changes:" in prepared.text
    assert "File: tests/test_app.py" in prepared.text
    assert "assert new()" in prepared.text
    assert "Summarized test changes:" not in prepared.text


def test_prepare_staged_diff_omits_lockfile_patch() -> None:
    raw_diff = """diff --git a/uv.lock b/uv.lock
new file mode 100644
--- /dev/null
+++ b/uv.lock
@@ -0,0 +1,2 @@
+package = "noisy"
+hash = "abc"
"""

    prepared = prepare_staged_diff(
        stat=" uv.lock | 2 ++\n",
        name_status="A\tuv.lock\n",
        raw_diff=raw_diff,
    )

    assert "uv.lock" in prepared.text
    assert "package = " not in prepared.text
    assert "lockfile diff omitted" in prepared.text
    assert "lockfile or generated changes" in prepared.text


def test_prepare_staged_diff_omits_large_patch() -> None:
    raw_diff = f"""diff --git a/src/large.py b/src/large.py
new file mode 100644
--- /dev/null
+++ b/src/large.py
@@ -0,0 +1 @@
+{"x" * 50}
"""

    prepared = prepare_staged_diff(
        stat=" src/large.py | 1 +\n",
        name_status="A\tsrc/large.py\n",
        raw_diff=raw_diff,
        max_file_patch_chars=40,
    )

    assert "src/large.py" in prepared.text
    assert "large diff omitted" in prepared.text
    assert "x" * 50 not in prepared.text


def test_prepare_staged_diff_stays_under_total_cap() -> None:
    raw_diff = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1 @@
-old_value = "abcdefghijklmnopqrstuvwxyz"
+new_value = "abcdefghijklmnopqrstuvwxyz"
diff --git a/src/other.py b/src/other.py
--- a/src/other.py
+++ b/src/other.py
@@ -1 +1 @@
-old_value = "abcdefghijklmnopqrstuvwxyz"
+new_value = "abcdefghijklmnopqrstuvwxyz"
"""

    prepared = prepare_staged_diff(
        stat=" src/app.py | 2 +-\n src/other.py | 2 +-\n",
        name_status="M\tsrc/app.py\nM\tsrc/other.py\n",
        raw_diff=raw_diff,
        max_total_chars=260,
    )

    assert len(prepared.text) <= 260
    assert "prompt under size limit" in prepared.text
    assert "\n- tests\n" not in prepared.text


def test_prepare_staged_diff_preserves_complete_omission_lines_under_cap() -> None:
    raw_diff = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1 @@
-old_value = "abcdefghijklmnopqrstuvwxyz"
+new_value = "abcdefghijklmnopqrstuvwxyz"
diff --git a/tests/test_app.py b/tests/test_app.py
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -1 +1 @@
-assert old()
+assert new()
diff --git a/uv.lock b/uv.lock
--- a/uv.lock
+++ b/uv.lock
@@ -1 +1 @@
-old
+package = "noisy"
"""

    prepared = prepare_staged_diff(
        stat=" src/app.py | 2 +-\n tests/test_app.py | 2 +-\n uv.lock | 2 +-\n",
        name_status="M\tsrc/app.py\nM\ttests/test_app.py\nM\tuv.lock\n",
        raw_diff=raw_diff,
        max_total_chars=700,
    )

    assert len(prepared.text) <= 700
    assert "- uv.lock: lockfile diff omitted" in prepared.text
    for line in prepared.text.splitlines():
        assert line != "- tests"


def test_prepare_staged_diff_reports_no_changes() -> None:
    prepared = prepare_staged_diff(stat="", name_status="", raw_diff="")

    assert prepared.has_changes is False
    assert prepared.text == ""
