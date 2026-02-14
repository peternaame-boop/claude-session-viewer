"""Group sessions by relative date for sidebar display."""

from datetime import datetime, timedelta
from enum import Enum


class DateGroup(str, Enum):
    TODAY = "Today"
    YESTERDAY = "Yesterday"
    THIS_WEEK = "This Week"
    THIS_MONTH = "This Month"
    OLDER = "Older"


def get_date_group(timestamp: float, now: datetime | None = None) -> DateGroup:
    """Classify a Unix timestamp into a relative date group."""
    if now is None:
        now = datetime.now()

    dt = datetime.fromtimestamp(timestamp)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    if dt >= today:
        return DateGroup.TODAY
    elif dt >= yesterday:
        return DateGroup.YESTERDAY
    elif dt >= week_start:
        return DateGroup.THIS_WEEK
    elif dt >= month_start:
        return DateGroup.THIS_MONTH
    else:
        return DateGroup.OLDER


def group_by_date(
    items: list,
    timestamp_key: str = "modified_at",
    now: datetime | None = None,
) -> dict[DateGroup, list]:
    """Group a list of items by date, preserving order within each group.

    Items must have the specified attribute or key with a Unix timestamp.
    Returns dict ordered: Today → Yesterday → This Week → This Month → Older.
    """
    groups: dict[DateGroup, list] = {g: [] for g in DateGroup}

    for item in items:
        if isinstance(item, dict):
            ts = item.get(timestamp_key, 0)
        else:
            ts = getattr(item, timestamp_key, 0)
        group = get_date_group(ts, now=now)
        groups[group].append(item)

    # Remove empty groups
    return {k: v for k, v in groups.items() if v}
