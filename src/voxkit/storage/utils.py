import os
from datetime import datetime
from pathlib import Path

from .config import STORAGE_ROOT, TEMP_STORAGE_ROOT


def get_storage_root() -> Path:
    """Get the root directory for storing VoxKit data."""
    if os.getenv("TESTING", "0") == "1":
        path = Path(TEMP_STORAGE_ROOT)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path
    if STORAGE_ROOT.startswith("~"):
        return Path(STORAGE_ROOT).expanduser()
    else:
        raise ValueError("STORAGE_ROOT must be a valid path starting with '~'")


def generate_unique_id(prefix: str = None) -> str:
    """Generate a unique identifier with the given prefix and current timestamp."""
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    if prefix:
        return f"{prefix}_{now}"
    return now


def readable_from_unique_id(date_str: str) -> str:
    """Convert a unique ID timestamp (YYYYMMDD_HHMMSS) to a human-readable format."""
    dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
    return dt.strftime("%B %d, %Y at %I:%M:%S %p")
