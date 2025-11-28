from datetime import datetime


def humanize_timestamp(ts: str) -> str:
    dt = datetime.fromisoformat(ts)
    return dt.strftime("%B %d, %Y at %I:%M:%S %p")
