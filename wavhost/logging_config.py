"""Logging configuration for Wavhost."""

import logging
import sys
from typing import Optional

DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SIMPLE_LOG_FORMAT = "%(levelname)s: %(message)s"
PACKAGE_LOGGER_NAME = "wavhost"


def _ensure_handler(
    logger: logging.Logger,
    level: int,
    format_string: Optional[str],
) -> None:
    """Attach Wavhost's stdout handler once without rewriting user handlers."""
    handler = next(
        (h for h in logger.handlers if getattr(h, "_wavhost_default_handler", False)),
        None,
    )
    if handler is None:
        if logger.handlers:
            # Respect logging configured by the embedding application.
            return
        handler = logging.StreamHandler(sys.stdout)
        handler._wavhost_default_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(format_string or SIMPLE_LOG_FORMAT))


def setup_logger(
    name: str,
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Set up a logger with consistent formatting.

    All ``wavhost.*`` loggers share one handler on the package logger. This is
    important for the server: configuring only ``wavhost.cli`` hides messages
    from sibling modules such as ``wavhost.backends``.

    Args:
        name: Logger name
        level: Logging level
        format_string: Custom format string (uses default if None)

    Returns:
        Configured logger instance
    """
    if name == PACKAGE_LOGGER_NAME or name.startswith(f"{PACKAGE_LOGGER_NAME}."):
        package_logger = logging.getLogger(PACKAGE_LOGGER_NAME)
        package_logger.setLevel(level)
        package_logger.propagate = False
        _ensure_handler(package_logger, level, format_string)

        logger = logging.getLogger(name)
        if logger is not package_logger:
            # Inherit the package level/handler instead of creating one handler
            # per module, which would duplicate output as records propagate.
            logger.setLevel(logging.NOTSET)
            logger.propagate = True
        return logger

    logger = logging.getLogger(name)
    logger.setLevel(level)
    _ensure_handler(logger, level, format_string)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a module logger without installing handlers as a library side effect."""
    return logging.getLogger(name)
