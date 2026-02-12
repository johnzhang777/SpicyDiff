"""Configuration module — reads GitHub Action inputs from environment variables."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional

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


def _parse_exclude_patterns(raw: Optional[str]) -> List[str]:
    """Parse a comma-separated string of glob patterns into a list."""
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


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

    # Tunable LLM parameters
    temperature: float = field(default=0.7)
    max_tokens: int = field(default=4096)

    # File filtering
    exclude_patterns: List[str] = field(default_factory=list)

    # Max diff size in characters sent to LLM
    max_diff_chars: int = field(default=60_000)

    # Dry-run: print review to logs without posting to GitHub
    dry_run: bool = field(default=False)

    @classmethod
    def from_env(cls) -> "Config":
        """Build a Config from environment variables injected by GitHub Actions."""
        # --- Required ---
        github_token = _require_env("INPUT_GITHUB_TOKEN")

        # Support both new (api-key) and old (openai-api-key) input names
        api_key = _optional_env("INPUT_API_KEY") or _require_env("INPUT_OPENAI_API_KEY")

        # --- Provider resolution ---
        provider_raw = _optional_env("INPUT_PROVIDER")
        base_url_raw = _optional_env("INPUT_BASE_URL") or _optional_env("INPUT_OPENAI_BASE_URL")
        model_raw = _optional_env("INPUT_MODEL")

        try:
            base_url, model = resolve_provider(provider_raw, base_url_raw, model_raw)
        except ValueError as exc:
            print(f"::error::{exc}")
            sys.exit(1)

        # --- Mode & language ---
        mode_raw = os.environ.get("INPUT_MODE", "ROAST").strip().upper()
        language_raw = os.environ.get("INPUT_LANGUAGE", "en").strip().lower()

        try:
            mode = Mode(mode_raw)
        except ValueError:
            print(f"::error::Invalid mode '{mode_raw}'. Must be one of: ROAST, PRAISE")
            sys.exit(1)

        try:
            language = Language(language_raw)
        except ValueError:
            print(f"::error::Invalid language '{language_raw}'. Must be one of: zh, en")
            sys.exit(1)

        # --- GitHub context ---
        github_repository = _require_env("GITHUB_REPOSITORY")

        pr_number_str = (
            _optional_env("INPUT_PR_NUMBER")
            or _optional_env("PR_NUMBER")
            or "0"
        )
        pr_number = int(pr_number_str)
        if pr_number <= 0:
            print("::error::Could not determine PR number from event context.")
            sys.exit(1)

        # --- Tunable LLM parameters ---
        temperature_str = os.environ.get("INPUT_TEMPERATURE", "0.7").strip()
        try:
            temperature = float(temperature_str)
        except ValueError:
            print(f"::error::Invalid temperature '{temperature_str}'. Must be a float.")
            sys.exit(1)

        max_tokens_str = os.environ.get("INPUT_MAX_TOKENS", "4096").strip()
        try:
            max_tokens = int(max_tokens_str)
        except ValueError:
            print(f"::error::Invalid max-tokens '{max_tokens_str}'. Must be an integer.")
            sys.exit(1)

        # --- Max diff size ---
        max_diff_chars_str = os.environ.get("INPUT_MAX_DIFF_CHARS", "60000").strip()
        try:
            max_diff_chars = int(max_diff_chars_str)
        except ValueError:
            max_diff_chars = 60_000

        # --- File filtering ---
        exclude_patterns = _parse_exclude_patterns(_optional_env("INPUT_EXCLUDE_PATTERNS"))

        # --- Dry run ---
        dry_run_raw = os.environ.get("INPUT_DRY_RUN", "false").strip().lower()
        dry_run = dry_run_raw in ("true", "1", "yes")

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
            temperature=temperature,
            max_tokens=max_tokens,
            exclude_patterns=exclude_patterns,
            max_diff_chars=max_diff_chars,
            dry_run=dry_run,
        )
