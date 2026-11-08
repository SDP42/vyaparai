"""Formatting helpers for sentences produced on the server (insights, warnings)."""

from decimal import ROUND_HALF_UP, Decimal


def inr(x: Decimal | int | float, *, signed: bool = False) -> str:
    """₹ with Indian digit grouping: 2390515 → ₹23,90,515. Whole rupees from ₹1,000 up."""
    d = Decimal(str(x))
    neg = d < 0
    d = abs(d)
    digits = (
        f"{d.quantize(Decimal('1'), rounding=ROUND_HALF_UP)}"
        if d >= 1000
        else f"{d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"
    )
    whole, _, frac = digits.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts: list[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join([*parts, tail])
    text = f"₹{whole}{'.' + frac if frac else ''}"
    if neg:
        return f"−{text}"
    return f"+{text}" if signed and d > 0 else text


def pct(x: Decimal | float, *, signed: bool = True) -> str:
    d = Decimal(str(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    sign = "+" if (signed and d > 0) else ("−" if d < 0 else "")
    return f"{sign}{abs(d)}%"
