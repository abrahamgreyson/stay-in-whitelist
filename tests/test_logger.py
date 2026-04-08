"""
Tests for logger configuration: log retention and rotation settings.
"""

from logging.handlers import TimedRotatingFileHandler

from stay_in_whitelist.logger import get_logger, reconfigure_logging


def test_get_logger_retention(tmp_path):
    """Verify get_logger() creates TimedRotatingFileHandler with 30-day retention."""
    log_name = 'test_logger_retention'
    logger = get_logger(log_name)

    handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
    assert len(handlers) >= 1, "Expected at least one TimedRotatingFileHandler"

    fh = handlers[0]
    assert fh.backupCount == 30, f"Expected backupCount=30, got {fh.backupCount}"
    assert fh.when == 'MIDNIGHT', f"Expected when='MIDNIGHT', got {fh.when}"


def test_reconfigure_logging_retention(tmp_path):
    """Verify reconfigure_logging() creates handler with 30-day retention."""
    log_name = 'test_reconfigure_retention'
    logger = get_logger(log_name)

    # Reconfigure with a temp log file path
    log_file = str(tmp_path / 'test.log')
    reconfigure_logging(log_file)

    handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
    assert len(handlers) >= 1, "Expected at least one TimedRotatingFileHandler after reconfigure"

    fh = handlers[0]
    assert fh.backupCount == 30, f"Expected backupCount=30, got {fh.backupCount}"
    assert fh.when == 'MIDNIGHT', f"Expected when='MIDNIGHT', got {fh.when}"
