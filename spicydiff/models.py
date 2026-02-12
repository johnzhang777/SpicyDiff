"""Pydantic models for LLM response validation."""

from __future__ import annotations

from enum import Enum
from typing import List

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
