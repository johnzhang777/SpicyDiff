"""GitHub interaction — post summary comments and inline review comments on a PR."""

from __future__ import annotations

import time
from typing import Dict, List, Set

from github import GithubException
from github.PullRequest import PullRequest

from .logger import log
from .models import Language, Mode, ReviewResult

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


def _build_summary_body(result: ReviewResult, mode: Mode, language: Language = Language.ZH) -> str:
    """Build a Markdown summary comment body."""
    emoji = _score_emoji(result.score)
    mode_label = _MODE_LABELS.get((mode, language), _MODE_LABELS[(mode, Language.EN)])
    header = f"{_MARKER}\n## SpicyDiff Review {emoji}\n\n"
    meta = f"**Mode**: {mode_label}  \n**Score**: {result.score}/100 {emoji}\n\n"
    body = f"---\n\n{result.summary}\n"
    return header + meta + body


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

    GitHub's ``create_review`` API is used to batch all comments into a single
    review so we don't flood the PR with individual comment notifications.
    """
    if not result.reviews:
        log.info("No inline reviews to post.")
        return

    # Gather the latest commit SHA (required by the review API)
    commits = list(pr.get_commits())
    if not commits:
        log.warning("No commits found in the PR; skipping inline comments.")
        return

    comments_payload: List[dict] = []
    for review in result.reviews:
        file_lines = changed_lines.get(review.file_path, set())
        # Only post if the line is actually part of the diff (GitHub API requirement)
        if review.line_number not in file_lines:
            log.warning(
                "Skipping comment on %s:%d (line not in diff).",
                review.file_path,
                review.line_number,
            )
            continue
        comments_payload.append(
            {
                "path": review.file_path,
                "line": review.line_number,
                "body": f"🌶️ **SpicyDiff**\n\n{review.comment}",
            }
        )

    if not comments_payload:
        log.info("All inline comments fell outside the diff; nothing to post.")
        return

    def _do_review():
        pr.create_review(
            commit=commits[-1],
            body="",
            event="COMMENT",
            comments=comments_payload,
        )

    _retry_github_call(_do_review)
    log.info("Posted %d inline review comment(s).", len(comments_payload))


def _retry_github_call(func, max_retries: int = 3) -> None:
    """Execute a GitHub API call with retries and exponential backoff.

    Handles rate-limiting (403/429) and server errors (5xx).
    """
    for attempt in range(max_retries):
        try:
            func()
            return
        except GithubException as exc:
            status = exc.status
            if status in (403, 429) or status >= 500:
                wait = 2 ** attempt  # 1s, 2s, 4s
                log.warning(
                    "GitHub API error %d (attempt %d/%d). Retrying in %ds...",
                    status, attempt + 1, max_retries, wait,
                )
                time.sleep(wait)
            else:
                raise  # non-retryable error
    # Final attempt — let it raise
    func()
