from datetime import datetime

from .config import STORAGE_ROOT


def get_storage_root() -> str:
    """Get the root directory for storing models and data."""
    if STORAGE_ROOT.startswith("~"):
        from pathlib import Path

        return str(Path(STORAGE_ROOT).expanduser())
    else:
        raise ValueError("STORAGE_ROOT must be a valid path starting with '~'")


def human_readable_date(date_str: str) -> str:
    """Convert YYYYMMDD_HHMMSS to 'MM-DD-YYYY H:MM am/pm' (e.g. 11-14-2001 6:00 pm)."""
    try:
        dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
        s = dt.strftime("%m-%d-%Y %I:%M %p")  # "11-14-2001 06:00 PM"
        date_part, time_part, ampm = s.split()
        hour, minute = time_part.split(":")
        hour = hour.lstrip("0")
        return f"{date_part} {hour}:{minute} {ampm.lower()}"
    except ValueError:
        return date_str

