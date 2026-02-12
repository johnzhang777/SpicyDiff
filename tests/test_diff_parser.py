"""Unit tests for the diff_parser module."""

from spicydiff.diff_parser import _should_ignore, FileDiff, PRDiff


class TestShouldIgnore:
    """Built-in ignore patterns."""

    def test_package_lock(self):
        assert _should_ignore("package-lock.json") is True

    def test_nested_lock(self):
        assert _should_ignore("frontend/yarn.lock") is True

    def test_image_png(self):
        assert _should_ignore("assets/logo.png") is True

    def test_image_jpg(self):
        assert _should_ignore("photo.jpeg") is True

    def test_normal_py(self):
        assert _should_ignore("src/main.py") is False

    def test_normal_ts(self):
        assert _should_ignore("components/App.tsx") is False

    def test_go_sum(self):
        assert _should_ignore("go.sum") is True

    def test_cargo_lock(self):
        assert _should_ignore("Cargo.lock") is True

    def test_svg(self):
        assert _should_ignore("icon.svg") is True

    def test_pdf(self):
        assert _should_ignore("report.pdf") is True

    def test_woff2(self):
        assert _should_ignore("fonts/inter.woff2") is True

    def test_normal_md(self):
        assert _should_ignore("README.md") is False


class TestShouldIgnoreExtraPatterns:
    """User-provided exclude patterns (glob)."""

    def test_extra_glob_match(self):
        assert _should_ignore("src/utils.test.js", ["*.test.js"]) is True

    def test_extra_glob_no_match(self):
        assert _should_ignore("src/utils.js", ["*.test.js"]) is False

    def test_extra_glob_directory(self):
        assert _should_ignore("docs/api/index.md", ["docs/**"]) is True

    def test_extra_glob_multiple(self):
        assert _should_ignore("e2e/login.spec.ts", ["*.spec.ts", "*.test.js"]) is True

    def test_extra_glob_none(self):
        assert _should_ignore("src/main.py", None) is False

    def test_extra_glob_empty_list(self):
        assert _should_ignore("src/main.py", []) is False


class TestFileDiff:
    def test_char_count(self):
        fd = FileDiff(path="a.py", patch="hello world")
        assert fd.char_count == 11


class TestPRDiff:
    def test_full_diff_text(self):
        fd1 = FileDiff(path="a.py", patch="patch-a")
        fd2 = FileDiff(path="b.py", patch="patch-b")
        pr_diff = PRDiff(files=[fd1, fd2])
        assert pr_diff.full_diff_text == "patch-a\npatch-b"

    def test_total_chars(self):
        fd1 = FileDiff(path="a.py", patch="1234")
        fd2 = FileDiff(path="b.py", patch="56789")
        pr_diff = PRDiff(files=[fd1, fd2])
        assert pr_diff.total_chars == 9

    def test_truncated_default_false(self):
        pr_diff = PRDiff(files=[])
        assert pr_diff.truncated is False

    def test_changed_line_map(self):
        fd = FileDiff(path="a.py", patch="p", added_lines={10: "x", 20: "y"})
        pr_diff = PRDiff(files=[fd])
        assert pr_diff.changed_line_map == {"a.py": {10, 20}}
