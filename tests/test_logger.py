"""Unit tests for the logger module."""

import logging

from spicydiff.logger import get_logger, GitHubActionsFormatter


class TestGetLogger:
    def test_returns_logger(self):
        logger = get_logger("test_spicydiff_logger")
        assert isinstance(logger, logging.Logger)

    def test_default_level_is_info(self):
        logger = get_logger("test_info_level")
        assert logger.level == logging.INFO

    def test_verbose_level_is_debug(self):
        logger = get_logger("test_debug_level", verbose=True)
        assert logger.level == logging.DEBUG

    def test_idempotent(self):
        logger1 = get_logger("test_idem")
        logger2 = get_logger("test_idem")
        assert logger1 is logger2
        assert len(logger1.handlers) == 1


class TestGitHubActionsFormatter:
    def test_error_prefix(self):
        formatter = GitHubActionsFormatter("%(message)s")
        record = logging.LogRecord("test", logging.ERROR, "", 0, "bad thing", (), None)
        assert formatter.format(record) == "::error::bad thing"

    def test_warning_prefix(self):
        formatter = GitHubActionsFormatter("%(message)s")
        record = logging.LogRecord("test", logging.WARNING, "", 0, "careful", (), None)
        assert formatter.format(record) == "::warning::careful"

    def test_info_no_prefix(self):
        formatter = GitHubActionsFormatter("%(message)s")
        record = logging.LogRecord("test", logging.INFO, "", 0, "just info", (), None)
        assert formatter.format(record) == "just info"

    def test_debug_no_prefix(self):
        formatter = GitHubActionsFormatter("%(message)s")
        record = logging.LogRecord("test", logging.DEBUG, "", 0, "debug msg", (), None)
        assert formatter.format(record) == "debug msg"
