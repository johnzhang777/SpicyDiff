"""Entry point for SpicyDiff — orchestrates the full review pipeline."""

from __future__ import annotations

import json
import os
import sys


def _resolve_pr_number() -> None:
    """Extract the PR number from the GitHub event payload and expose it via env."""
    if os.environ.get("INPUT_PR_NUMBER") or os.environ.get("PR_NUMBER"):
        return  # already set

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
        # Can't use logger here yet — config not loaded
        print(f"::warning::Failed to read GITHUB_EVENT_PATH: {exc}")


def run() -> None:
    """Execute the SpicyDiff review pipeline."""
    # Step 0: Resolve PR number from event context
    _resolve_pr_number()

    # Lazy imports so we get a nice error if dependencies are missing
    from .config import Config
    from .diff_parser import fetch_pr_diff, get_pr
    from .github_client import post_inline_comments, post_summary_comment
    from .llm_client import call_llm
    from .logger import log
    from .prompts import build_system_prompt, build_user_prompt

    # Step 1: Load configuration
    cfg = Config.from_env()
    provider_info = f"provider={cfg.provider}" if cfg.provider else f"base_url={cfg.base_url}"
    log.info(
        "SpicyDiff 🌶️  | mode=%s | lang=%s | model=%s | %s | temp=%.1f | max_tokens=%d%s",
        cfg.mode.value, cfg.language.value, cfg.model, provider_info,
        cfg.temperature, cfg.max_tokens,
        " | DRY RUN" if cfg.dry_run else "",
    )

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
        len(pr_diff.files),
        pr_diff.total_chars,
        " (diff truncated)" if pr_diff.truncated else "",
    )

    # Step 3: Build prompts
    system_prompt = build_system_prompt(cfg.mode, cfg.language)
    user_prompt = build_user_prompt(pr_diff.full_diff_text, cfg.language, pr_diff.truncated)

    # Step 4: Call LLM
    result = call_llm(
        api_key=cfg.api_key,
        model=cfg.model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        base_url=cfg.base_url,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
    )

    log.info("LLM Score: %d/100 | Inline reviews: %d", result.score, len(result.reviews))

    # Step 5: Post results to GitHub (or just log in dry-run mode)
    if cfg.dry_run:
        log.info("::group::Dry-run output (not posted to GitHub)")
        log.info("Summary: %s", result.summary)
        log.info("Score: %d/100", result.score)
        for r in result.reviews:
            log.info("  [%s:%d] %s", r.file_path, r.line_number, r.comment)
        log.info("::endgroup::")
        log.info("Dry-run complete. No comments were posted.")
    else:
        post_summary_comment(pr, result, cfg.mode, cfg.language)
        post_inline_comments(pr, result, pr_diff.changed_line_map)
        log.info("SpicyDiff review complete! 🌶️")


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
