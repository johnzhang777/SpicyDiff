"""Pydantic models for LLM response validation."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Mode(str, Enum):
    """Review personality mode."""

    ROAST = "ROAST"
    PRAISE = "PRAISE"
    SECURITY = "SECURITY"


class Language(str, Enum):
    """Output language."""

    ZH = "zh"
    EN = "en"


class InlineReview(BaseModel):
    """A single inline review comment targeting a specific line."""

    file_path: str = Field(..., description="Relative path of the reviewed file")
    line_number: int = Field(..., ge=1, description="1-based line number in the diff")
    comment: str = Field(..., min_length=1, description="The review comment text")


class ReviewResult(BaseModel):
    """Structured output returned by the LLM."""

    summary: str = Field(..., min_length=1, description="Overall PR review summary")
    score: int = Field(..., ge=0, le=100, description="Code quality score 0-100")
    reviews: List[InlineReview] = Field(default_factory=list, description="Inline review comments")


class FileReviewSummary(BaseModel):
    """Summary of a single file's review (used in multi-file mode)."""

    file_path: str
    score: int
    summary: str
    comment_count: int = 0


class FullReviewResult(BaseModel):
    """Extended review result that includes per-file breakdowns (multi-file mode)."""

    summary: str = Field(..., min_length=1, description="Overall merged summary")
    score: int = Field(..., ge=0, le=100, description="Combined score")
    reviews: List[InlineReview] = Field(default_factory=list)
    file_summaries: List[FileReviewSummary] = Field(default_factory=list)

    @property
    def has_file_breakdown(self) -> bool:
        return len(self.file_summaries) > 0
