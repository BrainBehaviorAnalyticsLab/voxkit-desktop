"""
Utility Module for VoxKit Storage
---------------------------------

This module provides utility functions for common VoxKit storage operations,
including path management and unique identifier generation.

API
---------
- get_storage_root: Get the root directory for storing VoxKit data.
- generate_unique_id: Generate a unique identifier with timestamp.
- readable_from_unique_id: Convert a unique ID to human-readable format.

Notes
-----
The storage root must be configured as a path starting with '~' to ensure
it references the user's home directory.
"""

from datetime import datetime
from functools import lru_cache
from pathlib import Path

from .config import STORAGE_ROOT


@lru_cache(maxsize=1)
def get_storage_root() -> Path:
    """Get the root directory for storing VoxKit data.

    This uses ~ (home directory) so it works regardless of how the app is launched.
    """
    if STORAGE_ROOT.startswith("~"):
        return Path(STORAGE_ROOT).expanduser()
    else:
        raise ValueError("STORAGE_ROOT must be a valid path starting with '~'")


def generate_unique_id(prefix: str | None = None) -> str:
    """Generate a unique identifier with the given prefix and current timestamp
    including microseconds.
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if prefix:
        return f"{prefix}_{now}"
    return now


def readable_from_unique_id(date_str: str) -> str:
    """Convert a unique ID timestamp (YYYYMMDD_HHMMSS_ffffff) to a human-readable format."""
    dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S_%f")
    return dt.strftime("%B %d, %Y at %I:%M:%S %p")
