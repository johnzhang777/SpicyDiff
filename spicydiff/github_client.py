"""GitHub interaction — post summary comments and inline review comments on a PR."""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Set

from github import GithubException
from github.PullRequest import PullRequest

from .logger import log
from .models import FileReviewSummary, FullReviewResult, Language, Mode, ReviewResult

# Hidden HTML marker to reliably identify SpicyDiff comments
_MARKER = "<!-- spicydiff-review -->"

# Score thresholds for emoji decoration
_SCORE_EMOJI = {
    range(0, 20): "🗑️",
    range(20, 40): "🔥",
    range(40, 60): "😐",
    range(60, 80): "👍",
    range(80, 101): "🚀",
}

# Mode labels per language
_MODE_LABELS = {
    (Mode.ROAST, Language.ZH): "🌶️ 地狱厨房模式 (ROAST)",
    (Mode.ROAST, Language.EN): "🌶️ Hell's Kitchen Mode (ROAST)",
    (Mode.PRAISE, Language.ZH): "🌈 夸夸群模式 (PRAISE)",
    (Mode.PRAISE, Language.EN): "🌈 Praise Mode (PRAISE)",
    (Mode.SECURITY, Language.ZH): "🔒 安全审计模式 (SECURITY)",
    (Mode.SECURITY, Language.EN): "🔒 Security Audit Mode (SECURITY)",
}


def _score_emoji(score: int) -> str:
    for rng, emoji in _SCORE_EMOJI.items():
        if score in rng:
            return emoji
    return ""


def _find_nearest_valid_line(target: int, valid_lines: Set[int], max_distance: int = 5) -> Optional[int]:
    """Find the nearest valid line number within max_distance of the target.

    The LLM sometimes returns a line number from the full file context
    rather than the exact added/changed line.  This finds the closest
    line that is actually in the diff so we can still post the comment.
    """
    if not valid_lines:
        return None
    best = None
    best_dist = max_distance + 1
    for line in valid_lines:
        dist = abs(line - target)
        if dist < best_dist:
            best_dist = dist
            best = line
    return best if best_dist <= max_distance else None


def _build_summary_body(result, mode: Mode, language: Language = Language.ZH) -> str:
    """Build a Markdown summary comment body.

    Accepts either a ReviewResult or FullReviewResult.  When a FullReviewResult
    with per-file breakdowns is provided, a detailed table is rendered.
    """
    emoji = _score_emoji(result.score)
    mode_label = _MODE_LABELS.get((mode, language), _MODE_LABELS[(mode, Language.EN)])

    parts = []
    parts.append(f"{_MARKER}\n## SpicyDiff Review {emoji}\n")
    parts.append(f"**Mode**: {mode_label}  ")
    parts.append(f"**Score**: {result.score}/100 {emoji}\n")
    parts.append("---\n")
    parts.append(f"{result.summary}\n")

    # Per-file breakdown (only for FullReviewResult from multi-file reviews)
    file_summaries = getattr(result, "file_summaries", [])
    if file_summaries:
        file_header = "### 📂 文件审查详情" if language == Language.ZH else "### 📂 Per-file Review Details"
        parts.append(f"\n{file_header}\n")

        for fs in file_summaries:
            file_emoji = _score_emoji(fs.score)
            # Each file gets a collapsible section with its full review
            parts.append(f"<details>")
            parts.append(f"<summary><b><code>{fs.file_path}</code></b> — {fs.score}/100 {file_emoji} ({fs.comment_count} comments)</summary>")
            parts.append(f"")
            parts.append(f"{fs.summary}")
            parts.append(f"")
            parts.append(f"</details>")
            parts.append(f"")

    # Stats footer
    review_count = len(result.reviews) if result.reviews else 0
    if review_count > 0:
        if language == Language.ZH:
            parts.append(f"\n> 💬 共 {review_count} 条行级评论（详见 Files Changed 页面）")
        else:
            parts.append(f"\n> 💬 {review_count} inline comment(s) — see the Files Changed tab")

    return "\n".join(parts)


def post_summary_comment(
    pr: PullRequest,
    result: ReviewResult,
    mode: Mode,
    language: Language = Language.ZH,
) -> None:
    """Post (or update) the summary comment on the PR."""
    body = _build_summary_body(result, mode, language)

    # Try to find an existing SpicyDiff comment to update (avoid spam)
    try:
        for comment in pr.get_issue_comments():
            if comment.body and _MARKER in comment.body:
                comment.edit(body)
                log.info("Updated existing SpicyDiff summary comment.")
                return
    except GithubException as exc:
        log.warning("Failed to list existing comments: %s", exc)

    _retry_github_call(lambda: pr.create_issue_comment(body))
    log.info("Created new SpicyDiff summary comment.")


def post_inline_comments(
    pr: PullRequest,
    result: ReviewResult,
    changed_lines: Dict[str, Set[int]],
) -> None:
    """Post inline review comments on the specific diff lines.

    Strategy:
    1. Try to post via the ``create_review`` API (batched, one notification).
    2. If that fails with 403 (permission denied), fall back to posting
       individual issue comments with file/line references.

    Line matching:
    - If the LLM returns a line not in the diff, try to find the nearest
      valid line within 5 lines (LLM often returns context line numbers).
    - If no nearby valid line exists, skip the comment.
    """
    if not result.reviews:
        log.info("No inline reviews to post.")
        return

    # Gather the latest commit SHA (required by the review API)
    commits = list(pr.get_commits())
    if not commits:
        log.warning("No commits found in the PR; skipping inline comments.")
        return

    # Build payload with line-number correction
    comments_payload: List[dict] = []
    for review in result.reviews:
        file_lines = changed_lines.get(review.file_path, set())
        target_line = review.line_number

        if target_line not in file_lines:
            # Try to snap to the nearest valid line
            nearest = _find_nearest_valid_line(target_line, file_lines)
            if nearest is not None:
                log.info(
                    "Snapped comment on %s:%d -> %d (nearest valid line).",
                    review.file_path, target_line, nearest,
                )
                target_line = nearest
            else:
                log.warning(
                    "Skipping comment on %s:%d (no valid line within range).",
                    review.file_path, review.line_number,
                )
                continue

        comments_payload.append(
            {
                "path": review.file_path,
                "line": target_line,
                "body": f"🌶️ **SpicyDiff**\n\n{review.comment}",
            }
        )

    if not comments_payload:
        log.info("All inline comments fell outside the diff; nothing to post.")
        return

    # Try the review API first (preferred — batched, single notification)
    try:
        pr.create_review(
            commit=commits[-1],
            body="",
            event="COMMENT",
            comments=comments_payload,
        )
        log.info("Posted %d inline review comment(s) via review API.", len(comments_payload))
        return
    except GithubException as exc:
        if exc.status == 403:
            log.warning(
                "Review API returned 403 (insufficient permissions). "
                "Falling back to individual issue comments."
            )
        elif exc.status == 422:
            log.warning(
                "Review API returned 422 (validation error, likely bad line numbers). "
                "Falling back to individual issue comments."
            )
        else:
            log.warning("Review API failed (%d). Falling back to issue comments.", exc.status)

    # Fallback: post as individual issue comments
    posted = 0
    for comment_data in comments_payload:
        body = (
            f"**{comment_data['path']}** (line {comment_data['line']})\n\n"
            f"{comment_data['body']}"
        )
        try:
            _retry_github_call(lambda b=body: pr.create_issue_comment(b))
            posted += 1
        except GithubException as exc:
            log.warning(
                "Failed to post comment on %s:%d — %s",
                comment_data["path"], comment_data["line"], exc,
            )
        # Avoid flooding: cap at 10 individual comments
        if posted >= 10:
            remaining = len(comments_payload) - posted
            if remaining > 0:
                log.info("Capped at 10 individual comments. %d more skipped.", remaining)
            break

    log.info("Posted %d inline comment(s) as issue comments (fallback).", posted)


def _retry_github_call(func, max_retries: int = 3) -> None:
    """Execute a GitHub API call with retries and exponential backoff.

    Only retries on rate-limiting (429) and server errors (5xx).
    403 (permission denied) is NOT retried — it's a permanent error.
    """
    for attempt in range(max_retries):
        try:
            func()
            return
        except GithubException as exc:
            status = exc.status
            if status == 429 or status >= 500:
                wait = 2 ** attempt  # 1s, 2s, 4s
                log.warning(
                    "GitHub API error %d (attempt %d/%d). Retrying in %ds...",
                    status, attempt + 1, max_retries, wait,
                )
                time.sleep(wait)
            else:
                raise  # non-retryable (including 403)
    # Final attempt — let it raise
    func()
