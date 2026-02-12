"""Unit tests for the models module."""

import pytest
from pydantic import ValidationError

from spicydiff.models import InlineReview, Mode, Language, ReviewResult


class TestMode:
    def test_roast(self):
        assert Mode("ROAST") == Mode.ROAST

    def test_praise(self):
        assert Mode("PRAISE") == Mode.PRAISE

    def test_invalid(self):
        with pytest.raises(ValueError):
            Mode("INVALID")


class TestLanguage:
    def test_zh(self):
        assert Language("zh") == Language.ZH

    def test_en(self):
        assert Language("en") == Language.EN


class TestInlineReview:
    def test_valid(self):
        r = InlineReview(file_path="src/main.py", line_number=42, comment="Bad naming")
        assert r.file_path == "src/main.py"
        assert r.line_number == 42

    def test_invalid_line_number(self):
        with pytest.raises(ValidationError):
            InlineReview(file_path="a.py", line_number=0, comment="Oops")

    def test_empty_comment(self):
        with pytest.raises(ValidationError):
            InlineReview(file_path="a.py", line_number=1, comment="")


class TestReviewResult:
    def test_valid_full(self):
        data = {
            "summary": "Terrible code!",
            "score": 15,
            "reviews": [
                {"file_path": "app.py", "line_number": 10, "comment": "Magic number!"}
            ],
        }
        result = ReviewResult.model_validate(data)
        assert result.score == 15
        assert len(result.reviews) == 1

    def test_valid_no_reviews(self):
        result = ReviewResult(summary="OK", score=50)
        assert result.reviews == []

    def test_score_out_of_range(self):
        with pytest.raises(ValidationError):
            ReviewResult(summary="Bad", score=101)

    def test_score_negative(self):
        with pytest.raises(ValidationError):
            ReviewResult(summary="Bad", score=-1)

    def test_empty_summary(self):
        with pytest.raises(ValidationError):
            ReviewResult(summary="", score=50)
