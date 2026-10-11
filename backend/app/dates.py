"""Calendar-date helpers. The client sends its own "today" so plans follow the student's time zone."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def weekday(d: date) -> str:
    return WEEKDAYS[d.weekday()]


def date_range(start: date, end: date) -> list[date]:
    """Every date from start to end, inclusive."""
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def parse_date(value: Any) -> date | None:
    """Parse "YYYY-MM-DD" from untrusted input (e.g. model output). Returns None if invalid."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
