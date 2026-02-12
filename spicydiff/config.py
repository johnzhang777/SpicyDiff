"""Configuration module — reads GitHub Action inputs from environment variables,
then merges with optional .spicydiff.yml repo config.

Priority: Action inputs > .spicydiff.yml > defaults.
"""

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


def _parse_list(raw: Optional[str]) -> List[str]:
    """Parse a comma-separated or newline-separated string into a list."""
    if not raw:
        return []
    # Support both comma and newline separation
    items = []
    for part in raw.replace("\n", ",").split(","):
        part = part.strip()
        if part:
            items.append(part)
    return items


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration derived from Action inputs + repo config."""

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

    # Custom review rules (from action input or .spicydiff.yml)
    custom_rules: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "Config":
        """Build a Config from environment variables injected by GitHub Actions."""
        # --- Required ---
        github_token = _require_env("INPUT_GITHUB_TOKEN")
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

        # --- Mode & language (from env, may be overridden by repo config) ---
        mode_raw = _optional_env("INPUT_MODE")
        language_raw = _optional_env("INPUT_LANGUAGE")

        # --- Tunable LLM parameters ---
        temperature_str = os.environ.get("INPUT_TEMPERATURE", "").strip()
        max_tokens_str = os.environ.get("INPUT_MAX_TOKENS", "").strip()
        max_diff_chars_str = os.environ.get("INPUT_MAX_DIFF_CHARS", "").strip()

        # --- File filtering & rules from action inputs ---
        exclude_from_input = _parse_list(_optional_env("INPUT_EXCLUDE_PATTERNS"))
        rules_from_input = _parse_list(_optional_env("INPUT_CUSTOM_RULES"))

        # --- Dry run ---
        dry_run_raw = os.environ.get("INPUT_DRY_RUN", "false").strip().lower()
        dry_run = dry_run_raw in ("true", "1", "yes")

        # --- GitHub context ---
        github_repository = _require_env("GITHUB_REPOSITORY")
        pr_number_str = _optional_env("INPUT_PR_NUMBER") or _optional_env("PR_NUMBER") or "0"
        pr_number = int(pr_number_str)
        if pr_number <= 0:
            print("::error::Could not determine PR number from event context.")
            sys.exit(1)

        # --- Load .spicydiff.yml (lazy import to avoid circular) ---
        from .repo_config import load_repo_config
        repo_cfg = load_repo_config()

        # --- Merge: Action input > repo config > defaults ---
        final_mode_raw = mode_raw or repo_cfg.mode or "ROAST"
        final_language_raw = language_raw or repo_cfg.language or "en"

        try:
            mode = Mode(final_mode_raw.strip().upper())
        except ValueError:
            print(f"::error::Invalid mode '{final_mode_raw}'. Must be one of: ROAST, PRAISE, SECURITY")
            sys.exit(1)

        try:
            language = Language(final_language_raw.strip().lower())
        except ValueError:
            print(f"::error::Invalid language '{final_language_raw}'. Must be one of: zh, en")
            sys.exit(1)

        # Temperature: input > repo config > 0.7
        temperature = 0.7
        if temperature_str:
            try:
                temperature = float(temperature_str)
            except ValueError:
                print(f"::error::Invalid temperature '{temperature_str}'.")
                sys.exit(1)
        elif repo_cfg.temperature is not None:
            temperature = repo_cfg.temperature

        # Max tokens
        max_tokens = 4096
        if max_tokens_str:
            try:
                max_tokens = int(max_tokens_str)
            except ValueError:
                print(f"::error::Invalid max-tokens '{max_tokens_str}'.")
                sys.exit(1)
        elif repo_cfg.max_tokens is not None:
            max_tokens = repo_cfg.max_tokens

        # Max diff chars
        max_diff_chars = 60_000
        if max_diff_chars_str:
            try:
                max_diff_chars = int(max_diff_chars_str)
            except ValueError:
                pass
        elif repo_cfg.max_diff_chars is not None:
            max_diff_chars = repo_cfg.max_diff_chars

        # Exclude patterns: merge both sources
        exclude_patterns = list(set(exclude_from_input + repo_cfg.exclude))

        # Custom rules: merge both sources (input rules first, then repo rules)
        custom_rules = rules_from_input + [r for r in repo_cfg.custom_rules if r not in rules_from_input]

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
            custom_rules=custom_rules,
        )
