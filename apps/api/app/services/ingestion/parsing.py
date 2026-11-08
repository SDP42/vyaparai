"""Value parsers tuned for Indian retail exports (₹, lakh-style commas, day-first dates)."""

import re
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from app.models.commerce import OrderStatus

DATE_ORDERS = {
    "dmy": (
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d %b %Y",
        "%d-%b-%Y",
        "%d %B %Y",
    ),
    "mdy": ("%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%b %d %Y", "%B %d %Y"),
    "ymd": ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"),
}
_TIME_SUFFIXES = ("", " %H:%M", " %H:%M:%S", "T%H:%M:%S", " %I:%M %p", " %I:%M:%S %p")

_STATUS = {
    "completed": OrderStatus.COMPLETED,
    "complete": OrderStatus.COMPLETED,
    "paid": OrderStatus.COMPLETED,
    "delivered": OrderStatus.COMPLETED,
    "closed": OrderStatus.COMPLETED,
    "success": OrderStatus.COMPLETED,
    "cancelled": OrderStatus.CANCELLED,
    "canceled": OrderStatus.CANCELLED,
    "void": OrderStatus.CANCELLED,
    "returned": OrderStatus.RETURNED,
    "return": OrderStatus.RETURNED,
    "refunded": OrderStatus.RETURNED,
    "pending": OrderStatus.PENDING,
    "open": OrderStatus.PENDING,
    "processing": OrderStatus.PENDING,
}


class ParseError(ValueError):
    pass


def parse_number(v: Any) -> Decimal:
    if isinstance(v, int | float | Decimal) and not isinstance(v, bool):
        return Decimal(str(v))
    s = str(v).strip()
    if not s:
        raise ParseError("is empty")
    negative = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[₹,\s]|rs\.?|inr", "", s.strip("()"), flags=re.IGNORECASE)
    try:
        d = Decimal(s)
    except InvalidOperation as exc:
        raise ParseError(f"'{v}' is not a number") from exc
    if not d.is_finite():
        raise ParseError(f"'{v}' is not a number")
    return -d if negative else d


def parse_date(v: Any, order: str = "dmy") -> datetime:
    """Parse a date/datetime. ``order`` resolves ambiguous dates (India defaults to day-first)."""
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    if isinstance(v, date):
        return datetime.combine(v, time(), tzinfo=UTC)
    s = re.sub(r"\s+", " ", str(v).strip())
    if not s:
        raise ParseError("is empty")
    # ISO first (unambiguous), then the preferred order, then the others.
    orders = ["ymd", order] + [o for o in DATE_ORDERS if o not in ("ymd", order)]
    for o in orders:
        for base in DATE_ORDERS[o]:
            for suffix in _TIME_SUFFIXES:
                try:
                    return datetime.strptime(s, base + suffix).replace(tzinfo=UTC)
                except ValueError:
                    continue
    raise ParseError(f"'{v}' is not a recognised date")


def parse_status(v: Any) -> OrderStatus:
    s = str(v).strip().lower()
    if not s:
        return OrderStatus.COMPLETED
    if s in _STATUS:
        return _STATUS[s]
    raise ParseError(f"unknown status '{v}'")
