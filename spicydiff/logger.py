"""Structured logging for SpicyDiff with GitHub Actions annotation support."""

from __future__ import annotations

import logging
import sys


class GitHubActionsFormatter(logging.Formatter):
    """Formatter that maps log levels to GitHub Actions annotations."""

    _LEVEL_MAP = {
        logging.DEBUG: "",
        logging.INFO: "",
        logging.WARNING: "::warning::",
        logging.ERROR: "::error::",
        logging.CRITICAL: "::error::",
    }

    def format(self, record: logging.LogRecord) -> str:
        prefix = self._LEVEL_MAP.get(record.levelno, "")
        message = super().format(record)
        if prefix:
            return f"{prefix}{message}"
        return message


def get_logger(name: str = "spicydiff", verbose: bool = False) -> logging.Logger:
    """Create or retrieve the SpicyDiff logger.

    Returns a logger that writes to stdout with GitHub Actions-compatible
    annotations for warnings and errors.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(GitHubActionsFormatter("%(message)s"))
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False
    return logger


# Module-level convenience instance
log = get_logger()
