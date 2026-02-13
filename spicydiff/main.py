"""Entry point for SpicyDiff — orchestrates the full review pipeline.

Supports two review strategies:
- **Single-pass**: Small PRs (≤3 files) — send entire diff in one LLM call.
- **Multi-file**: Larger PRs — review each file individually with smart context,
  then merge per-file results into a final summary.
"""

from __future__ import annotations

import json
import os
import sys
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .diff_parser import PRDiff
    from .models import ReviewResult

# Threshold: PRs with more than this many files use multi-file review
MULTI_FILE_THRESHOLD = 3


def _resolve_pr_number() -> None:
    """Extract the PR number from the GitHub event payload and expose it via env."""
    if os.environ.get("INPUT_PR_NUMBER") or os.environ.get("PR_NUMBER"):
        return

    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path or not os.path.isfile(event_path):
        return

    try:
        with open(event_path, "r", encoding="utf-8") as fh:
            event = json.load(fh)
        pr_number = event.get("pull_request", {}).get("number")
        if pr_number:
            os.environ["PR_NUMBER"] = str(pr_number)
    except Exception as exc:
        print(f"::warning::Failed to read GITHUB_EVENT_PATH: {exc}")


def run() -> None:
    """Execute the SpicyDiff review pipeline."""
    _resolve_pr_number()

    from .config import Config
    from .context import extract_surrounding_context, fetch_file_content
    from .diff_parser import PRDiff, fetch_pr_diff, get_pr
    from .github_client import post_inline_comments, post_summary_comment
    from .llm_client import call_llm
    from .logger import log
    from .models import InlineReview, ReviewResult
    from .prompts import (
        build_file_review_prompt,
        build_merge_summary_prompt,
        build_system_prompt,
        build_user_prompt,
    )

    # Step 1: Load configuration
    cfg = Config.from_env()
    provider_info = f"provider={cfg.provider}" if cfg.provider else f"base_url={cfg.base_url}"
    log.info(
        "SpicyDiff 🌶️  | mode=%s | lang=%s | model=%s | %s | temp=%.1f | max_tokens=%d%s",
        cfg.mode.value, cfg.language.value, cfg.model, provider_info,
        cfg.temperature, cfg.max_tokens,
        " | DRY RUN" if cfg.dry_run else "",
    )
    if cfg.custom_rules:
        log.info("Custom rules: %d rule(s) loaded", len(cfg.custom_rules))

    # Step 2: Fetch and parse the PR diff
    log.info("Fetching PR #%d diff from %s...", cfg.pr_number, cfg.github_repository)
    pr = get_pr(cfg.github_token, cfg.github_repository, cfg.pr_number)
    pr_diff = fetch_pr_diff(
        pr,
        exclude_patterns=cfg.exclude_patterns or None,
        max_diff_chars=cfg.max_diff_chars,
    )

    if not pr_diff.files:
        log.info("No reviewable files found in the PR diff. Exiting.")
        return

    log.info(
        "Found %d file(s) to review (%d chars).%s",
        len(pr_diff.files), pr_diff.total_chars,
        " (diff truncated)" if pr_diff.truncated else "",
    )

    # Step 3: Build system prompt (shared across all calls)
    system_prompt = build_system_prompt(cfg.mode, cfg.language, cfg.custom_rules or None)

    # Step 4: Choose review strategy
    if len(pr_diff.files) <= MULTI_FILE_THRESHOLD:
        result = _single_pass_review(cfg, system_prompt, pr_diff)
    else:
        result = _multi_file_review(cfg, system_prompt, pr_diff, pr)

    log.info("LLM Score: %d/100 | Inline reviews: %d", result.score, len(result.reviews))

    # Step 5: Post results — everything goes into one summary comment
    if cfg.dry_run:
        _print_dry_run(log, result)
    else:
        post_summary_comment(pr, result, cfg.mode, cfg.language)
        log.info("SpicyDiff review complete! 🌶️")


def _single_pass_review(cfg, system_prompt: str, pr_diff: PRDiff) -> ReviewResult:
    """Review all files in a single LLM call (for small PRs)."""
    from .llm_client import call_llm
    from .logger import log
    from .prompts import build_user_prompt

    log.info("Using single-pass review (≤%d files).", MULTI_FILE_THRESHOLD)
    user_prompt = build_user_prompt(pr_diff.full_diff_text, cfg.language, pr_diff.truncated)

    return call_llm(
        api_key=cfg.api_key,
        model=cfg.model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        base_url=cfg.base_url,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
    )


def _multi_file_review(cfg, system_prompt: str, pr_diff: PRDiff, pr):
    """Review each file individually, then merge results.

    For each file:
    1. Fetch the full file content (for smart context).
    2. Extract surrounding function/class bodies.
    3. Call LLM with per-file diff + context.
    4. Collect all inline reviews + per-file summaries.

    Finally, call LLM again to merge per-file summaries into a cohesive overall review.
    Returns a FullReviewResult with per-file breakdowns.
    """
    from .context import extract_surrounding_context, fetch_file_content
    from .llm_client import call_llm
    from .logger import log
    from .models import FileReviewSummary, FullReviewResult, InlineReview
    from .prompts import build_file_review_prompt, build_merge_summary_prompt

    log.info("Using multi-file review (%d files).", len(pr_diff.files))

    all_reviews: List[InlineReview] = []
    file_review_summaries: List[FileReviewSummary] = []
    file_summary_texts: List[str] = []

    for i, file_diff in enumerate(pr_diff.files, 1):
        log.info("::group::Reviewing file %d/%d: %s", i, len(pr_diff.files), file_diff.path)

        # Smart context: fetch full file and extract enclosing blocks
        context_code = None
        if file_diff.added_lines:
            full_source = fetch_file_content(pr, file_diff.path)
            if full_source:
                context_code = extract_surrounding_context(
                    full_source, set(file_diff.added_lines.keys())
                )
                if context_code:
                    log.info("Extracted %d chars of surrounding context.", len(context_code))

        # Build per-file prompt
        user_prompt = build_file_review_prompt(
            file_path=file_diff.path,
            diff_text=file_diff.patch,
            language=cfg.language,
            context_code=context_code,
        )

        # Call LLM for this file
        file_result = call_llm(
            api_key=cfg.api_key,
            model=cfg.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            base_url=cfg.base_url,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )

        all_reviews.extend(file_result.reviews)

        # Store per-file summary for the table
        file_review_summaries.append(FileReviewSummary(
            file_path=file_diff.path,
            score=file_result.score,
            summary=file_result.summary,
            comment_count=len(file_result.reviews),
        ))
        file_summary_texts.append(
            f"- **{file_diff.path}** (score: {file_result.score}): {file_result.summary}"
        )

        log.info("  Score: %d/100 | Comments: %d", file_result.score, len(file_result.reviews))
        log.info("::endgroup::")

    # Merge: generate an overall summary from per-file results
    log.info("Generating merged summary from %d file reviews...", len(file_summary_texts))
    merge_prompt = build_merge_summary_prompt("\n".join(file_summary_texts), cfg.language)

    merge_result = call_llm(
        api_key=cfg.api_key,
        model=cfg.model,
        system_prompt=system_prompt,
        user_prompt=merge_prompt,
        base_url=cfg.base_url,
        temperature=cfg.temperature,
        max_tokens=1024,
    )

    return FullReviewResult(
        summary=merge_result.summary,
        score=merge_result.score,
        reviews=all_reviews,
        file_summaries=file_review_summaries,
    )


def _print_dry_run(log, result: ReviewResult) -> None:
    """Print the review to logs without posting."""
    log.info("::group::Dry-run output (not posted to GitHub)")
    log.info("Summary: %s", result.summary)
    log.info("Score: %d/100", result.score)
    for r in result.reviews:
        log.info("  [%s:%d] %s", r.file_path, r.line_number, r.comment)
    log.info("::endgroup::")
    log.info("Dry-run complete. No comments were posted.")


def main() -> None:
    """CLI entry point with basic error handling."""
    try:
        run()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)
    except Exception as exc:
        print(f"::error::SpicyDiff failed with an unexpected error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
