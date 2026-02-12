"""Smart context extraction — fetch surrounding function/class bodies for changed lines.

When we know which lines changed, we can ask the GitHub API for the full file content
and extract the enclosing function or class to give the LLM better understanding.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from github.PullRequest import PullRequest
from github.Repository import Repository

from .logger import log

# Max characters of context per file (prevent sending entire huge files)
MAX_CONTEXT_CHARS = 3000

# Patterns that indicate a function/class/method boundary in common languages
_BLOCK_PATTERNS = [
    # Python: def / class / async def
    re.compile(r"^(\s*)(def |async def |class )\w+"),
    # JS/TS: function / const x = / class / export
    re.compile(r"^(\s*)(function |const |let |var |class |export |async function )\w+"),
    # Go: func
    re.compile(r"^(\s*)func[\s(]"),
    # Java/C#/Kotlin: public/private/protected ... method or class
    re.compile(r"^(\s*)(public |private |protected |internal |static |override |fun |void |int |string |boolean )\w+"),
    # Rust: fn / pub fn / impl / struct
    re.compile(r"^(\s*)(pub )?(fn |impl |struct |enum |trait )\w+"),
]


def fetch_file_content(pr: PullRequest, file_path: str) -> Optional[str]:
    """Fetch the full content of a file at the PR's head branch.

    Returns None if the file can't be fetched.
    """
    try:
        repo = pr.base.repo
        ref = pr.head.sha
        content_file = repo.get_contents(file_path, ref=ref)
        if hasattr(content_file, "decoded_content"):
            return content_file.decoded_content.decode("utf-8", errors="replace")
    except Exception as exc:
        log.debug("Could not fetch content for %s: %s", file_path, exc)
    return None


def extract_surrounding_context(
    full_source: str,
    changed_lines: Set[int],
    max_chars: int = MAX_CONTEXT_CHARS,
) -> Optional[str]:
    """Extract the enclosing function/class bodies for the changed lines.

    Parameters
    ----------
    full_source : str
        Complete file content.
    changed_lines : set[int]
        Set of 1-based line numbers that were changed.
    max_chars : int
        Maximum total characters to return.

    Returns
    -------
    str | None
        Extracted context with line numbers, or None if nothing useful found.
    """
    if not changed_lines or not full_source:
        return None

    lines = full_source.splitlines()
    if not lines:
        return None

    # Find the enclosing block for each changed line
    context_ranges: List[Tuple[int, int]] = []

    for line_no in sorted(changed_lines):
        if line_no < 1 or line_no > len(lines):
            continue
        start, end = _find_enclosing_block(lines, line_no - 1)  # 0-indexed
        context_ranges.append((start, end))

    if not context_ranges:
        return None

    # Merge overlapping ranges
    merged = _merge_ranges(context_ranges)

    # Build context string with line numbers
    parts = []
    total_chars = 0
    for start, end in merged:
        for i in range(start, min(end + 1, len(lines))):
            line_text = f"{i + 1:4d} | {lines[i]}"
            if total_chars + len(line_text) > max_chars:
                parts.append("     | ... (truncated)")
                return "\n".join(parts)
            parts.append(line_text)
            total_chars += len(line_text) + 1
        parts.append("")  # blank line between ranges

    result = "\n".join(parts).strip()
    return result if result else None


def _find_enclosing_block(lines: List[str], target_idx: int) -> Tuple[int, int]:
    """Find the start and end of the function/class containing the target line.

    Uses indentation-based heuristics that work for Python, JS, Go, Java, etc.
    """
    # Walk backwards to find the nearest block start
    block_start = target_idx
    target_indent = _get_indent(lines[target_idx]) if target_idx < len(lines) else 0

    for i in range(target_idx - 1, -1, -1):
        line = lines[i]
        if not line.strip():
            continue
        indent = _get_indent(line)
        # Check if this line is a block definition at a lower indent level
        if indent < target_indent or any(p.match(line) for p in _BLOCK_PATTERNS):
            block_start = i
            if any(p.match(line) for p in _BLOCK_PATTERNS):
                break

    # Walk forwards to find the end of the block
    block_end = target_idx
    if block_start < len(lines):
        start_indent = _get_indent(lines[block_start])
        for i in range(target_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip():
                block_end = i
                continue
            indent = _get_indent(line)
            if indent <= start_indent and any(p.match(line) for p in _BLOCK_PATTERNS):
                break
            block_end = i

    # Clamp: don't include more than ~50 lines per block
    max_block_lines = 50
    if block_end - block_start > max_block_lines:
        # Center around the target line
        half = max_block_lines // 2
        block_start = max(block_start, target_idx - half)
        block_end = min(block_end, target_idx + half)

    return block_start, block_end


def _get_indent(line: str) -> int:
    """Return the number of leading whitespace characters."""
    return len(line) - len(line.lstrip())


def _merge_ranges(ranges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Merge overlapping or adjacent line ranges."""
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end + 2:  # merge if overlapping or within 2 lines
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged
