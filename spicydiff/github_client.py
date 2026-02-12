"""GitHub interaction — post summary comments and inline review comments on a PR."""

from __future__ import annotations

from typing import Dict, Set

from github.PullRequest import PullRequest

from .models import Mode, ReviewResult

# Score thresholds for emoji decoration
_SCORE_EMOJI = {
    range(0, 20): "🗑️",
    range(20, 40): "🔥",
    range(40, 60): "😐",
    range(60, 80): "👍",
    range(80, 101): "🚀",
}


def _score_emoji(score: int) -> str:
    for rng, emoji in _SCORE_EMOJI.items():
        if score in rng:
            return emoji
    return ""


def _build_summary_body(result: ReviewResult, mode: Mode) -> str:
    """Build a Markdown summary comment body."""
    emoji = _score_emoji(result.score)
    mode_label = "🌶️ 地狱厨房模式 (ROAST)" if mode == Mode.ROAST else "🌈 夸夸群模式 (PRAISE)"
    header = f"## SpicyDiff Review {emoji}\n\n"
    meta = f"**Mode**: {mode_label}  \n**Score**: {result.score}/100 {emoji}\n\n"
    body = f"---\n\n{result.summary}\n"
    return header + meta + body


def post_summary_comment(pr: PullRequest, result: ReviewResult, mode: Mode) -> None:
    """Post (or update) the summary comment on the PR."""
    body = _build_summary_body(result, mode)

    # Try to find an existing SpicyDiff comment to update (avoid spam)
    for comment in pr.get_issue_comments():
        if comment.body and comment.body.startswith("## SpicyDiff Review"):
            comment.edit(body)
            print("Updated existing SpicyDiff summary comment.")
            return

    pr.create_issue_comment(body)
    print("Created new SpicyDiff summary comment.")


def post_inline_comments(
    pr: PullRequest,
    result: ReviewResult,
    changed_lines: Dict[str, Set[int]],
) -> None:
    """Post inline review comments on the specific diff lines.

    GitHub's "create_review" API is used to batch all comments into a single
    review so we don't flood the PR with individual comment notifications.
    """
    if not result.reviews:
        print("No inline reviews to post.")
        return

    # Gather the latest commit SHA (required by the review API)
    commits = list(pr.get_commits())
    if not commits:
        print("::warning::No commits found in the PR; skipping inline comments.")
        return
    head_sha = commits[-1].sha

    comments_payload = []
    for review in result.reviews:
        file_lines = changed_lines.get(review.file_path, set())
        # Only post if the line is actually part of the diff (GitHub API requirement)
        if review.line_number not in file_lines:
            print(
                f"::warning::Skipping comment on {review.file_path}:{review.line_number} "
                "(line not in diff)."
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
        print("All inline comments fell outside the diff; nothing to post.")
        return

    pr.create_review(
        commit=commits[-1],
        body="",
        event="COMMENT",
        comments=comments_payload,
    )
    print(f"Posted {len(comments_payload)} inline review comment(s).")
