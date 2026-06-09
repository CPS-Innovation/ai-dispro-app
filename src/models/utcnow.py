from datetime import datetime, timezone

def _utcnow() -> datetime:
    """Return the current UTC time (evaluated per row at insert time)."""
    return datetime.now(timezone.utc)