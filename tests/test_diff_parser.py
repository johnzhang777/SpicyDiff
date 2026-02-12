"""Unit tests for the diff_parser module."""

from spicydiff.diff_parser import _should_ignore


class TestShouldIgnore:
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
