"""Application logging setup.

Configures a rotating file log at ``~/.voxkit/logs/voxkit.log`` and exposes
a hook for attaching a GUI handler. ``VOXKIT_DEBUG=1`` in the environment
raises the file log level to DEBUG.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 3

LOG_DIR = Path.home() / ".voxkit" / "logs"
LOG_FILE = LOG_DIR / "voxkit.log"

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    log_file: Optional[Path] = None,
) -> RotatingFileHandler:
    """Configure the root logger with a rotating file handler.

    Idempotent — calling more than once has no effect beyond the first call.

    Args:
        max_bytes: Max size in bytes before rotation.
        backup_count: Number of rotated files to retain.
        log_file: Override the log file path (primarily for tests).

    Returns:
        The installed RotatingFileHandler.
    """
    global _configured

    target = log_file or LOG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    debug_enabled = os.environ.get("VOXKIT_DEBUG") == "1"
    root.setLevel(logging.DEBUG if debug_enabled else logging.INFO)

    if _configured:
        for handler in root.handlers:
            if isinstance(handler, RotatingFileHandler):
                return handler

    handler = RotatingFileHandler(
        target,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    handler.setLevel(logging.DEBUG if debug_enabled else logging.INFO)
    root.addHandler(handler)

    _configured = True
    logging.getLogger(__name__).info(
        "Logging initialized (debug=%s, file=%s)", debug_enabled, target
    )
    return handler


def reset_logging() -> None:
    """Remove handlers installed by :func:`setup_logging`. Test helper."""
    global _configured
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    _configured = False
