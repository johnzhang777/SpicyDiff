"""Load project-level configuration from a .spicydiff.yml file in the repo root.

This allows teams to commit shared SpicyDiff settings (mode, language, custom
rules, exclude patterns) alongside their code, without touching the workflow YAML.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .logger import log

# Supported config file names (checked in order)
_CONFIG_FILENAMES = [
    ".spicydiff.yml",
    ".spicydiff.yaml",
    "spicydiff.yml",
    "spicydiff.yaml",
]


@dataclass
class RepoConfig:
    """Settings loaded from the repo's .spicydiff.yml."""

    mode: Optional[str] = None
    language: Optional[str] = None
    custom_rules: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    max_diff_chars: Optional[int] = None

    @property
    def has_overrides(self) -> bool:
        return any([
            self.mode, self.language, self.custom_rules,
            self.exclude, self.temperature is not None,
            self.max_tokens is not None, self.max_diff_chars is not None,
        ])


def load_repo_config(workspace_dir: Optional[str] = None) -> RepoConfig:
    """Attempt to load a .spicydiff.yml from the workspace root.

    Parameters
    ----------
    workspace_dir : str | None
        Workspace / repo root directory.  Defaults to ``GITHUB_WORKSPACE`` env
        or current working directory.

    Returns
    -------
    RepoConfig
        Parsed config, or an empty RepoConfig if no config file is found.
    """
    root = workspace_dir or os.environ.get("GITHUB_WORKSPACE", os.getcwd())

    for filename in _CONFIG_FILENAMES:
        path = os.path.join(root, filename)
        if os.path.isfile(path):
            log.info("Found repo config: %s", path)
            return _parse_config_file(path)

    log.debug("No .spicydiff.yml found in %s", root)
    return RepoConfig()


def _parse_config_file(path: str) -> RepoConfig:
    """Parse a YAML config file into a RepoConfig."""
    try:
        # Use a safe YAML loader; fall back to simple parsing if PyYAML is not available
        import yaml  # type: ignore[import-untyped]
        with open(path, "r", encoding="utf-8") as fh:
            data: Dict[str, Any] = yaml.safe_load(fh) or {}
    except ImportError:
        log.warning("PyYAML not installed; .spicydiff.yml will be ignored. pip install pyyaml to enable.")
        return RepoConfig()
    except Exception as exc:
        log.warning("Failed to parse %s: %s", path, exc)
        return RepoConfig()

    if not isinstance(data, dict):
        log.warning("%s is not a valid YAML mapping; ignoring.", path)
        return RepoConfig()

    config = RepoConfig()

    # mode
    if "mode" in data and isinstance(data["mode"], str):
        config.mode = data["mode"].strip().upper()

    # language
    if "language" in data and isinstance(data["language"], str):
        config.language = data["language"].strip().lower()

    # custom_rules / rules
    rules_key = "rules" if "rules" in data else "custom_rules"
    rules_raw = data.get(rules_key, [])
    if isinstance(rules_raw, list):
        config.custom_rules = [str(r).strip() for r in rules_raw if r]

    # exclude
    exclude_raw = data.get("exclude", [])
    if isinstance(exclude_raw, list):
        config.exclude = [str(e).strip() for e in exclude_raw if e]

    # temperature
    if "temperature" in data:
        try:
            config.temperature = float(data["temperature"])
        except (ValueError, TypeError):
            pass

    # max_tokens
    if "max_tokens" in data or "max-tokens" in data:
        val = data.get("max_tokens") or data.get("max-tokens")
        try:
            config.max_tokens = int(val)
        except (ValueError, TypeError):
            pass

    # max_diff_chars
    if "max_diff_chars" in data or "max-diff-chars" in data:
        val = data.get("max_diff_chars") or data.get("max-diff-chars")
        try:
            config.max_diff_chars = int(val)
        except (ValueError, TypeError):
            pass

    log.info(
        "Repo config loaded: %d custom rules, %d exclude patterns",
        len(config.custom_rules), len(config.exclude),
    )
    return config
