"""Comparison ranges and change calculations."""

from datetime import date, timedelta
from decimal import Decimal

from app.services.analytics.metrics import MetricDef
from app.services.analytics.types import CENT, CompareMode

YEAR_SHIFT_DAYS = 364  # 52 weeks, so weekdays line up


def resolve_compare(date_from: date, date_to: date, mode: CompareMode) -> tuple[date, date] | None:
    """Return the comparison (from, to), or None when no comparison is requested."""
    if mode == "none":
        return None
    days = (date_to - date_from).days + 1
    if mode == "previous_year":
        shift = timedelta(days=YEAR_SHIFT_DAYS)
        return date_from - shift, date_to - shift
    prev_to = date_from - timedelta(days=1)
    return prev_to - timedelta(days=days - 1), prev_to


def compare_label(mode: CompareMode) -> str:
    return {
        "previous_period": "previous period of the same length",
        "previous_year": "same weekdays last year (364 days earlier)",
        "none": "no comparison",
    }[mode]


def change(
    metric: MetricDef, current: Decimal | None, previous: Decimal | None
) -> tuple[Decimal | None, Decimal | None]:
    """(absolute change, relative change in %) or percentage points for percent metrics.

    Relative change is ``None`` when the previous value is zero or missing, never infinity.
    """
    if current is None or previous is None:
        return None, None
    delta = (current - previous).quantize(CENT)
    if metric.compare_in_points:
        return delta, None
    if previous == 0:
        return delta, None
    return delta, ((current - previous) / abs(previous) * 100).quantize(CENT)


def default_range(max_date: date | None, today: date) -> tuple[date, date]:
    """Last 30 days ending at the latest order date (imported history is rarely 'today')."""
    end = max_date or today
    return end - timedelta(days=29), end


def pick_granularity(days: int) -> str:
    if days <= 45:
        return "day"
    if days <= 200:
        return "week"
    return "month"


def bucket_start(d: date, granularity: str) -> date:
    if granularity == "week":
        return d - timedelta(days=d.weekday())  # Monday
    if granularity == "month":
        return d.replace(day=1)
    return d
