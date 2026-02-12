"""Fetch and parse the PR diff from GitHub."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from github import Github
from github.PullRequest import PullRequest
from unidiff import PatchSet

# Files we never want to review
_IGNORE_PATTERNS: List[str] = [
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
    # Generated files
    r"(^|/)\.gitignore$",
    r"(^|/)\.DS_Store$",
]

_IGNORE_RE = [re.compile(p, re.IGNORECASE) for p in _IGNORE_PATTERNS]


def _should_ignore(file_path: str) -> bool:
    return any(pattern.search(file_path) for pattern in _IGNORE_RE)


@dataclass
class FileDiff:
    """Parsed diff for a single file."""

    path: str
    patch: str  # raw unified-diff text for this file
    added_lines: Dict[int, str] = field(default_factory=dict)  # line_no -> content


@dataclass
class PRDiff:
    """Aggregated diff information for an entire PR."""

    files: List[FileDiff] = field(default_factory=list)

    @property
    def full_diff_text(self) -> str:
        """Concatenate all file patches into a single diff string."""
        return "\n".join(f.patch for f in self.files)

    @property
    def changed_line_map(self) -> Dict[str, Set[int]]:
        """Map file_path -> set of added/modified line numbers."""
        return {f.path: set(f.added_lines.keys()) for f in self.files}


def get_pr(github_token: str, repo_full_name: str, pr_number: int) -> PullRequest:
    """Return the PyGithub PullRequest object."""
    g = Github(github_token)
    repo = g.get_repo(repo_full_name)
    return repo.get_pull(pr_number)


def fetch_pr_diff(pr: PullRequest) -> PRDiff:
    """Fetch the diff for a PR, parse it, and filter out ignored files."""
    files: List[FileDiff] = []

    for pr_file in pr.get_files():
        path = pr_file.filename
        if _should_ignore(path):
            continue
        patch_text = pr_file.patch
        if not patch_text:
            continue

        # Parse added lines using unidiff
        added_lines: Dict[int, str] = {}
        try:
            # unidiff expects a full unified diff header; we synthesize one
            full_patch = f"--- a/{path}\n+++ b/{path}\n{patch_text}"
            patch_set = PatchSet(full_patch)
            for patched_file in patch_set:
                for hunk in patched_file:
                    for line in hunk:
                        if line.is_added:
                            added_lines[line.target_line_no] = line.value
        except Exception:
            # If parsing fails, still include the raw patch
            pass

        files.append(FileDiff(path=path, patch=patch_text, added_lines=added_lines))

    return PRDiff(files=files)
