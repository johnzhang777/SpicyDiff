"""Unit tests for the github_client module."""

from spicydiff.github_client import _score_emoji, _build_summary_body, _MARKER
from spicydiff.models import Language, Mode, ReviewResult


class TestScoreEmoji:
    def test_trash(self):
        assert _score_emoji(5) == "🗑️"

    def test_fire(self):
        assert _score_emoji(30) == "🔥"

    def test_neutral(self):
        assert _score_emoji(50) == "😐"

    def test_thumbsup(self):
        assert _score_emoji(70) == "👍"

    def test_rocket(self):
        assert _score_emoji(95) == "🚀"

    def test_boundary_zero(self):
        assert _score_emoji(0) == "🗑️"

    def test_boundary_100(self):
        assert _score_emoji(100) == "🚀"


class TestBuildSummaryBody:
    def test_roast_mode_zh(self):
        result = ReviewResult(summary="Awful code!", score=12, reviews=[])
        body = _build_summary_body(result, Mode.ROAST, Language.ZH)
        assert "SpicyDiff Review" in body
        assert "ROAST" in body
        assert "12/100" in body
        assert "Awful code!" in body
        assert "地狱厨房" in body

    def test_praise_mode_zh(self):
        result = ReviewResult(summary="Brilliant!", score=99, reviews=[])
        body = _build_summary_body(result, Mode.PRAISE, Language.ZH)
        assert "PRAISE" in body
        assert "99/100" in body
        assert "夸夸群" in body

    def test_roast_mode_en(self):
        result = ReviewResult(summary="Terrible!", score=10, reviews=[])
        body = _build_summary_body(result, Mode.ROAST, Language.EN)
        assert "Hell's Kitchen" in body
        assert "地狱厨房" not in body

    def test_praise_mode_en(self):
        result = ReviewResult(summary="Amazing!", score=95, reviews=[])
        body = _build_summary_body(result, Mode.PRAISE, Language.EN)
        assert "Praise Mode" in body
        assert "夸夸群" not in body

    def test_contains_html_marker(self):
        result = ReviewResult(summary="Test", score=50, reviews=[])
        body = _build_summary_body(result, Mode.ROAST, Language.EN)
        assert _MARKER in body

    def test_marker_is_hidden_html_comment(self):
        assert _MARKER.startswith("<!--")
        assert _MARKER.endswith("-->")
