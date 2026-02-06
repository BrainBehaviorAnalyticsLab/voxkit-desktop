"""Utility Module for VoxKit Storage.

This module provides utility functions for common VoxKit storage operations,
including path management and unique identifier generation.

API
---
- **get_storage_root**: Get the root directory for storing VoxKit data
- **generate_unique_id**: Generate a unique identifier with timestamp
- **readable_from_unique_id**: Convert a unique ID to human-readable format
- **is_first_launch**: Check if this is the first launch of the application
- **mark_first_launch_complete**: Mark the first launch as complete
- **save_json**: Save JSON data to a file within storage

Notes
-----
- The storage root uses tilde (~) notation to ensure it references the user's home directory
- Unique IDs are based on timestamps with microsecond precision (YYYYMMDD_HHMMSS_ffffff)
- The storage root path is cached for performance using lru_cache
- First launch tracking uses a flag file (.first_launch_complete) in the storage root
"""

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import STORAGE_ROOT


@lru_cache(maxsize=1)
def get_storage_root() -> Path:
    """Get the root directory for storing VoxKit data.

    Returns:
        Path to the storage root directory (expanded from tilde notation)

    Raises:
        ValueError: If STORAGE_ROOT does not start with tilde (~)
    """
    if STORAGE_ROOT.startswith("~"):
        return Path(STORAGE_ROOT).expanduser()
    else:
        raise ValueError("STORAGE_ROOT must be a valid path starting with '~'")


def generate_unique_id(prefix: str | None = None) -> str:
    """Generate a unique identifier with the given prefix and current timestamp.

    Args:
        prefix: Optional prefix to prepend to the timestamp

    Returns:
        Unique identifier string in format: [prefix_]YYYYMMDD_HHMMSS_ffffff
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if prefix:
        return f"{prefix}_{now}"
    return now


def readable_from_unique_id(date_str: str) -> str:
    """Convert a unique ID timestamp to a human-readable format.

    Args:
        date_str: Timestamp string in format YYYYMMDD_HHMMSS_ffffff

    Returns:
        Human-readable date string (e.g., "January 01, 2024 at 12:00:00 PM")
    """
    dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S_%f")
    return dt.strftime("%B %d, %Y at %I:%M:%S %p")


def is_first_launch() -> bool:
    """Check if this is the first launch of the application.

    Returns:
        True if this is the first launch, False otherwise
    """
    storage_root = get_storage_root()
    flag_file = storage_root / ".first_launch_complete"
    return not flag_file.exists()


def mark_first_launch_complete() -> None:
    """Mark the first launch as complete by creating a flag file."""
    storage_root = get_storage_root()
    storage_root.mkdir(parents=True, exist_ok=True)
    flag_file = storage_root / ".first_launch_complete"
    flag_file.touch()


def save_json(file_path: Path, data: dict[str, Any]) -> None:
    """Save JSON data to a file within storage.

    Creates parent directories if they don't exist.

    Args:
        file_path: Path to the JSON file (should be within storage root)
        data: Dictionary to serialize as JSON
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
