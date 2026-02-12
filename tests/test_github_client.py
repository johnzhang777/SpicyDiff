"""Unit tests for the github_client module."""

from spicydiff.github_client import _score_emoji, _build_summary_body
from spicydiff.models import Mode, ReviewResult


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
    def test_roast_mode(self):
        result = ReviewResult(summary="Awful code!", score=12, reviews=[])
        body = _build_summary_body(result, Mode.ROAST)
        assert "SpicyDiff Review" in body
        assert "ROAST" in body
        assert "12/100" in body
        assert "Awful code!" in body

    def test_praise_mode(self):
        result = ReviewResult(summary="Brilliant!", score=99, reviews=[])
        body = _build_summary_body(result, Mode.PRAISE)
        assert "PRAISE" in body
        assert "99/100" in body
