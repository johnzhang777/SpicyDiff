"""LLM client — sends prompts to an OpenAI-compatible API and validates the response."""

from __future__ import annotations

import json
import sys
from typing import Optional

from openai import OpenAI
from pydantic import ValidationError

from .models import ReviewResult


def call_llm(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    base_url: str = "https://api.openai.com/v1",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> ReviewResult:
    """Call the LLM and return a validated ReviewResult.

    Raises
    ------
    SystemExit
        When the response cannot be parsed into valid JSON or fails schema validation.
    """
    client = OpenAI(api_key=api_key, base_url=base_url)

    print(f"::group::Calling LLM ({model})")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    raw_content: Optional[str] = response.choices[0].message.content
    print(f"Raw LLM response:\n{raw_content}")
    print("::endgroup::")

    if not raw_content:
        print("::error::LLM returned an empty response.")
        sys.exit(1)

    # Strip possible markdown code fences that some models add despite instructions
    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        cleaned = cleaned.split("\n", 1)[-1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    # Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(f"::error::Failed to parse LLM output as JSON: {exc}")
        print(f"Raw output was:\n{raw_content}")
        sys.exit(1)

    # Validate with Pydantic
    try:
        result = ReviewResult.model_validate(data)
    except ValidationError as exc:
        print(f"::error::LLM output failed schema validation:\n{exc}")
        sys.exit(1)

    return result
