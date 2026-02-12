"""Configuration module — reads GitHub Action inputs from environment variables."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Optional

from .models import Language, Mode
from .providers import resolve_provider


def _require_env(name: str) -> str:
    """Return an environment variable or exit with a clear error message."""
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"::error::Missing required input: {name}")
        sys.exit(1)
    return value


def _optional_env(name: str) -> Optional[str]:
    """Return an environment variable or None if empty/missing."""
    value = os.environ.get(name, "").strip()
    return value if value else None


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration derived from Action inputs."""

    github_token: str
    api_key: str
    model: str
    mode: Mode
    language: Language
    github_repository: str
    pr_number: int
    base_url: str = field(default="https://api.openai.com/v1")
    provider: Optional[str] = field(default=None)

    @classmethod
    def from_env(cls) -> "Config":
        """Build a Config from environment variables injected by GitHub Actions."""
        github_token = _require_env("INPUT_GITHUB_TOKEN")
        api_key = _require_env("INPUT_API_KEY")

        # Read raw optional inputs
        provider_raw = _optional_env("INPUT_PROVIDER")
        base_url_raw = _optional_env("INPUT_BASE_URL")
        model_raw = _optional_env("INPUT_MODEL")

        # --- Backward compatibility ---
        # Support old input names (openai-api-key, openai-base-url) for smooth migration
        if not api_key:
            api_key = _require_env("INPUT_OPENAI_API_KEY")
        if not base_url_raw:
            base_url_raw = _optional_env("INPUT_OPENAI_BASE_URL")

        # Resolve provider → (base_url, model)
        try:
            base_url, model = resolve_provider(provider_raw, base_url_raw, model_raw)
        except ValueError as exc:
            print(f"::error::{exc}")
            sys.exit(1)

        mode_raw = os.environ.get("INPUT_MODE", "ROAST").strip().upper()
        language_raw = os.environ.get("INPUT_LANGUAGE", "en").strip().lower()

        # Validate mode
        try:
            mode = Mode(mode_raw)
        except ValueError:
            print(f"::error::Invalid mode '{mode_raw}'. Must be one of: ROAST, PRAISE")
            sys.exit(1)

        # Validate language
        try:
            language = Language(language_raw)
        except ValueError:
            print(f"::error::Invalid language '{language_raw}'. Must be one of: zh, en")
            sys.exit(1)

        # GitHub context
        github_repository = _require_env("GITHUB_REPOSITORY")

        # PR number — sourced from GITHUB_EVENT or explicit input
        pr_number_str = os.environ.get("INPUT_PR_NUMBER", "").strip()
        if not pr_number_str:
            pr_number_str = os.environ.get("PR_NUMBER", "0")
        pr_number = int(pr_number_str)
        if pr_number <= 0:
            print("::error::Could not determine PR number from event context.")
            sys.exit(1)

        return cls(
            github_token=github_token,
            api_key=api_key,
            model=model,
            mode=mode,
            language=language,
            github_repository=github_repository,
            pr_number=pr_number,
            base_url=base_url,
            provider=provider_raw,
        )
