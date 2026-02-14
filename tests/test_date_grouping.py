"""Tests for date grouping utility."""

from datetime import datetime, timedelta
import pytest
from claude_session_viewer.utils.date_grouping import (
    DateGroup,
    get_date_group,
    group_by_date,
)


@pytest.fixture
def now():
    """Fixed 'now' for deterministic tests: Wednesday Feb 14, 2026 at noon."""
    return datetime(2026, 2, 14, 12, 0, 0)


class TestGetDateGroup:
    def test_today(self, now):
        ts = now.timestamp() - 3600  # 1 hour ago
        assert get_date_group(ts, now=now) == DateGroup.TODAY

    def test_yesterday(self, now):
        ts = (now - timedelta(days=1)).replace(hour=15).timestamp()
        assert get_date_group(ts, now=now) == DateGroup.YESTERDAY

    def test_this_week(self, now):
        # now is Wednesday, so Monday is 2 days ago
        ts = (now - timedelta(days=2)).replace(hour=10).timestamp()
        assert get_date_group(ts, now=now) == DateGroup.THIS_WEEK

    def test_this_month(self, now):
        # Feb 5 is this month but not this week
        ts = datetime(2026, 2, 5, 10, 0).timestamp()
        assert get_date_group(ts, now=now) == DateGroup.THIS_MONTH

    def test_older(self, now):
        ts = datetime(2026, 1, 15, 10, 0).timestamp()
        assert get_date_group(ts, now=now) == DateGroup.OLDER

    def test_far_past(self, now):
        ts = datetime(2025, 6, 1, 10, 0).timestamp()
        assert get_date_group(ts, now=now) == DateGroup.OLDER


class TestGroupByDate:
    def test_groups_items(self, now):
        items = [
            {"name": "a", "modified_at": now.timestamp()},
            {"name": "b", "modified_at": (now - timedelta(days=1, hours=2)).timestamp()},
            {"name": "c", "modified_at": (now - timedelta(days=30)).timestamp()},
        ]
        groups = group_by_date(items, now=now)
        assert len(groups[DateGroup.TODAY]) == 1
        assert groups[DateGroup.TODAY][0]["name"] == "a"
        assert DateGroup.OLDER in groups

    def test_empty_groups_excluded(self, now):
        items = [{"name": "x", "modified_at": now.timestamp()}]
        groups = group_by_date(items, now=now)
        assert DateGroup.OLDER not in groups
        assert DateGroup.TODAY in groups

    def test_empty_input(self, now):
        assert group_by_date([], now=now) == {}

    def test_custom_key(self, now):
        items = [{"name": "a", "created": now.timestamp()}]
        groups = group_by_date(items, timestamp_key="created", now=now)
        assert DateGroup.TODAY in groups
