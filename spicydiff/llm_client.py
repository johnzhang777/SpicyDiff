"""LLM client — sends prompts to an OpenAI-compatible API and validates the response."""

from __future__ import annotations

import json
import sys
from typing import Optional

from openai import OpenAI
from pydantic import ValidationError

from .logger import log
from .models import ReviewResult

# Default retry/timeout settings
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 120  # seconds


def call_llm(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    base_url: str = "https://api.openai.com/v1",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    max_retries: int = DEFAULT_MAX_RETRIES,
    timeout: int = DEFAULT_TIMEOUT,
) -> ReviewResult:
    """Call the LLM and return a validated ReviewResult.

    Features:
    - Automatic retry with exponential backoff for transient errors (429, 500, etc.)
    - Configurable timeout per request
    - Strips markdown code fences from the response
    - Validates output against the Pydantic schema

    Raises
    ------
    SystemExit
        When the response cannot be parsed into valid JSON or fails schema validation
        after all retries are exhausted.
    """
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        max_retries=max_retries,
        timeout=timeout,
    )

    log.info("::group::Calling LLM (%s) | temperature=%.1f | max_tokens=%d", model, temperature, max_tokens)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        log.error("LLM API call failed after %d retries: %s", max_retries, exc)
        sys.exit(1)

    raw_content: Optional[str] = response.choices[0].message.content
    log.info("Raw LLM response:\n%s", raw_content)
    log.info("::endgroup::")

    if not raw_content:
        log.error("LLM returned an empty response.")
        sys.exit(1)

    # Strip possible markdown code fences that some models add despite instructions
    cleaned = _strip_code_fences(raw_content)

    # Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        log.error("Failed to parse LLM output as JSON: %s", exc)
        log.error("Raw output was:\n%s", raw_content)
        sys.exit(1)

    # Validate with Pydantic
    try:
        result = ReviewResult.model_validate(data)
    except ValidationError as exc:
        log.error("LLM output failed schema validation:\n%s", exc)
        sys.exit(1)

    return result


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from the LLM response."""
    cleaned = text.strip()

    # Remove opening fence (```json, ```JSON, ``` etc.)
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
        else:
            cleaned = cleaned[3:]

    # Remove closing fence
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return cleaned.strip()
