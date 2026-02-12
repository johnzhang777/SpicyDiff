"""Fetch and parse the PR diff from GitHub."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from github import Github
from github.PullRequest import PullRequest
from unidiff import PatchSet

from .logger import log

# ---------------------------------------------------------------------------
# Default ignore patterns (always skipped unless user overrides)
# ---------------------------------------------------------------------------
_DEFAULT_IGNORE_PATTERNS: List[str] = [
    # Lock files
    r"(^|/)package-lock\.json$",
    r"(^|/)yarn\.lock$",
    r"(^|/)pnpm-lock\.yaml$",
    r"(^|/)Pipfile\.lock$",
    r"(^|/)poetry\.lock$",
    r"(^|/)go\.sum$",
    r"(^|/)Cargo\.lock$",
    # Binary / image files
    r"\.(png|jpe?g|gif|svg|ico|webp|bmp|woff2?|ttf|eot|mp[34]|avi|mov|zip|tar|gz|pdf)$",
    # OS / generated files
    r"(^|/)\.DS_Store$",
]

_DEFAULT_IGNORE_RE = [re.compile(p, re.IGNORECASE) for p in _DEFAULT_IGNORE_PATTERNS]

# Maximum diff size (in characters) sent to LLM in a single request.
# Roughly ~60k chars ≈ ~15k tokens — safe for most models' context windows.
DEFAULT_MAX_DIFF_CHARS = 60_000


def _should_ignore(file_path: str, extra_patterns: Optional[List[str]] = None) -> bool:
    """Check if a file should be excluded from review.

    Parameters
    ----------
    file_path : str
        Relative file path from the repo root.
    extra_patterns : list[str] | None
        Additional glob patterns provided by the user (e.g. ``["*.test.js", "docs/**"]``).
    """
    # Built-in regex patterns
    if any(pattern.search(file_path) for pattern in _DEFAULT_IGNORE_RE):
        return True

    # User-provided glob patterns
    if extra_patterns:
        for pat in extra_patterns:
            if fnmatch.fnmatch(file_path, pat):
                return True

    return False


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FileDiff:
    """Parsed diff for a single file."""

    path: str
    patch: str  # raw unified-diff text for this file
    added_lines: Dict[int, str] = field(default_factory=dict)  # line_no -> content

    @property
    def char_count(self) -> int:
        return len(self.patch)


@dataclass
class PRDiff:
    """Aggregated diff information for an entire PR."""

    files: List[FileDiff] = field(default_factory=list)
    truncated: bool = False  # True if diff was trimmed to fit the size limit

    @property
    def full_diff_text(self) -> str:
        """Concatenate all file patches into a single diff string."""
        return "\n".join(f.patch for f in self.files)

    @property
    def total_chars(self) -> int:
        return sum(f.char_count for f in self.files)

    @property
    def changed_line_map(self) -> Dict[str, Set[int]]:
        """Map file_path -> set of added/modified line numbers."""
        return {f.path: set(f.added_lines.keys()) for f in self.files}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_pr(github_token: str, repo_full_name: str, pr_number: int) -> PullRequest:
    """Return the PyGithub PullRequest object."""
    g = Github(github_token)
    repo = g.get_repo(repo_full_name)
    return repo.get_pull(pr_number)


def fetch_pr_diff(
    pr: PullRequest,
    exclude_patterns: Optional[List[str]] = None,
    max_diff_chars: int = DEFAULT_MAX_DIFF_CHARS,
) -> PRDiff:
    """Fetch the diff for a PR, parse it, and filter out ignored files.

    Parameters
    ----------
    pr : PullRequest
        The GitHub PR object.
    exclude_patterns : list[str] | None
        Additional glob patterns to exclude (e.g. ``["*.test.js"]``).
    max_diff_chars : int
        Maximum total characters of diff text to include.  Files are added
        in the order GitHub returns them; once the budget is exceeded the
        remaining files are skipped and ``PRDiff.truncated`` is set to True.
    """
    files: List[FileDiff] = []
    total_chars = 0
    truncated = False
    skipped_files: List[str] = []

    for pr_file in pr.get_files():
        path = pr_file.filename
        if _should_ignore(path, exclude_patterns):
            log.debug("Skipping ignored file: %s", path)
            continue

        patch_text = pr_file.patch
        if not patch_text:
            continue

        # Check size budget
        patch_len = len(patch_text)
        if total_chars + patch_len > max_diff_chars:
            skipped_files.append(path)
            truncated = True
            continue

        # Parse added lines using unidiff
        added_lines: Dict[int, str] = {}
        try:
            full_patch = f"--- a/{path}\n+++ b/{path}\n{patch_text}"
            patch_set = PatchSet(full_patch)
            for patched_file in patch_set:
                for hunk in patched_file:
                    for line in hunk:
                        if line.is_added:
                            added_lines[line.target_line_no] = line.value
        except Exception as exc:
            log.warning("Failed to parse diff for %s: %s (raw patch still included)", path, exc)

        files.append(FileDiff(path=path, patch=patch_text, added_lines=added_lines))
        total_chars += patch_len

    if skipped_files:
        log.warning(
            "Diff size limit reached (%d chars). Skipped %d file(s): %s",
            max_diff_chars,
            len(skipped_files),
            ", ".join(skipped_files[:5]) + ("..." if len(skipped_files) > 5 else ""),
        )

    return PRDiff(files=files, truncated=truncated)
