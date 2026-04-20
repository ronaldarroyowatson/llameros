"""Logging configuration helpers for Llameros."""
from __future__ import annotations

import logging


def resolve_log_level(rules: dict | None = None, debug: bool = False) -> int:
    """Resolve the effective log level from CLI debug mode or config."""
    if debug:
        return logging.DEBUG

    rules = rules or {}
    configured = str(rules.get("LOG_LEVEL", rules.get("log_level", "INFO"))).upper()
    return getattr(logging, configured, logging.INFO)


def configure_logging(rules: dict | None = None, debug: bool = False) -> int:
    """Configure root logging without disrupting existing test handlers."""
    level = resolve_log_level(rules=rules, debug=debug)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)

    return level