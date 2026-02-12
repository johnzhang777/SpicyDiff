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
    from .prompts import build_system_prompt, build_user_prompt

    # Step 1: Load configuration
    cfg = Config.from_env()
    provider_info = f"provider={cfg.provider}" if cfg.provider else f"base_url={cfg.base_url}"
    print(f"SpicyDiff 🌶️  | mode={cfg.mode.value} | lang={cfg.language.value} | model={cfg.model} | {provider_info}")

    # Step 2: Fetch and parse the PR diff
    pr = get_pr(cfg.github_token, cfg.github_repository, cfg.pr_number)
    pr_diff = fetch_pr_diff(pr)

    if not pr_diff.files:
        print("No reviewable files found in the PR diff. Exiting.")
        return

    print(f"Found {len(pr_diff.files)} file(s) to review.")

    # Step 3: Build prompts
    system_prompt = build_system_prompt(cfg.mode, cfg.language)
    user_prompt = build_user_prompt(pr_diff.full_diff_text)

    # Step 4: Call LLM
    result = call_llm(
        api_key=cfg.api_key,
        model=cfg.model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        base_url=cfg.base_url,
    )

    print(f"LLM Score: {result.score}/100 | Inline reviews: {len(result.reviews)}")

    # Step 5: Post results to GitHub
    post_summary_comment(pr, result, cfg.mode)
    post_inline_comments(pr, result, pr_diff.changed_line_map)

    print("SpicyDiff review complete! 🌶️")


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
