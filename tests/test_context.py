"""Unit tests for the context module."""

from spicydiff.context import extract_surrounding_context, _find_enclosing_block, _merge_ranges


class TestExtractSurroundingContext:
    def test_basic_python_function(self):
        source = (
            "import os\n"
            "\n"
            "def hello():\n"
            "    x = 1\n"
            "    y = 2\n"
            "    return x + y\n"
            "\n"
            "def other():\n"
            "    pass\n"
        )
        # Line 4 is "x = 1" inside hello()
        result = extract_surrounding_context(source, {4})
        assert result is not None
        assert "hello" in result
        assert "x = 1" in result

    def test_no_changed_lines(self):
        result = extract_surrounding_context("some code", set())
        assert result is None

    def test_empty_source(self):
        result = extract_surrounding_context("", {1})
        assert result is None

    def test_none_source(self):
        result = extract_surrounding_context(None, {1})
        assert result is None

    def test_max_chars_truncation(self):
        source = "\n".join(f"line {i}" for i in range(100))
        result = extract_surrounding_context(source, {50}, max_chars=100)
        assert result is not None
        assert "truncated" in result

    def test_multiple_changed_lines(self):
        source = (
            "def foo():\n"
            "    a = 1\n"
            "    b = 2\n"
            "\n"
            "def bar():\n"
            "    c = 3\n"
            "    d = 4\n"
        )
        result = extract_surrounding_context(source, {2, 6})
        assert result is not None
        assert "foo" in result
        assert "bar" in result

    def test_line_numbers_in_output(self):
        source = "line1\nline2\nline3\n"
        result = extract_surrounding_context(source, {2})
        assert result is not None
        # Should contain line numbers
        assert "2" in result


class TestFindEnclosingBlock:
    def test_inside_function(self):
        lines = ["def foo():", "    x = 1", "    y = 2", "", "def bar():", "    pass"]
        start, end = _find_enclosing_block(lines, 1)  # "x = 1"
        assert start == 0  # should find "def foo()"
        assert end >= 1

    def test_at_function_def(self):
        lines = ["def foo():", "    pass"]
        start, end = _find_enclosing_block(lines, 0)
        assert start == 0


class TestMergeRanges:
    def test_no_overlap(self):
        assert _merge_ranges([(0, 5), (10, 15)]) == [(0, 5), (10, 15)]

    def test_overlapping(self):
        assert _merge_ranges([(0, 5), (4, 10)]) == [(0, 10)]

    def test_adjacent(self):
        assert _merge_ranges([(0, 5), (6, 10)]) == [(0, 10)]

    def test_empty(self):
        assert _merge_ranges([]) == []

    def test_single(self):
        assert _merge_ranges([(3, 7)]) == [(3, 7)]

    def test_unsorted(self):
        assert _merge_ranges([(10, 15), (0, 5)]) == [(0, 5), (10, 15)]
