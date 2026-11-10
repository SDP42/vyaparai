"""Did the campaign work? Treatment against holdout, with honest uncertainty.

Customers in the holdout were chosen the same way as those messaged but were not contacted, so any
difference in what the two groups bought afterwards is the campaign's effect (plus chance). Chance is
measured here: a 95% interval for the difference in purchase rate (Newcombe, built from Wilson intervals)
and a bootstrap interval for the difference in spend and profit per customer. A result whose interval
includes zero is reported as inconclusive, not as a win or a loss.
"""

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

Z = 1.96
MIN_PER_GROUP = 30  # below this, intervals are too wide to mean much


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def newcombe_diff(k1: int, n1: int, k0: int, n0: int) -> tuple[float, float, float]:
    """Difference in proportions (group 1 minus group 0) with a 95% interval."""
    p1, p0 = (k1 / n1 if n1 else 0.0), (k0 / n0 if n0 else 0.0)
    l1, u1 = wilson(k1, n1)
    l0, u0 = wilson(k0, n0)
    d = p1 - p0
    return (
        d,
        d - math.sqrt((p1 - l1) ** 2 + (u0 - p0) ** 2),
        d + math.sqrt((u1 - p1) ** 2 + (p0 - l0) ** 2),
    )


def bootstrap_diff(
    a: list[float], b: list[float], reps: int = 2000, seed: int = 11
) -> tuple[float, float, float]:
    """Difference in means (a minus b) with a percentile 95% interval. Seeded, so the result is repeatable."""
    if not a or not b:
        return 0.0, 0.0, 0.0
    rng = np.random.default_rng(seed)
    xa, xb = np.array(a), np.array(b)
    da = rng.choice(xa, size=(reps, len(xa))).mean(axis=1)
    db = rng.choice(xb, size=(reps, len(xb))).mean(axis=1)
    diff = da - db
    return (
        float(xa.mean() - xb.mean()),
        float(np.percentile(diff, 2.5)),
        float(np.percentile(diff, 97.5)),
    )


def needed_per_group(base_rate: float, lift_points: float = 5.0) -> int:
    """Customers needed in each group to see a lift of ``lift_points`` percentage points (80% power)."""
    p = min(max(base_rate, 0.02), 0.98)
    delta = lift_points / 100
    return math.ceil(2 * ((Z + 0.84) ** 2) * p * (1 - p) / (delta**2))


@dataclass(slots=True)
class Person:
    bought: bool
    revenue: float
    profit: float


def verdict(lo: float, hi: float) -> str:
    return "positive" if lo > 0 else "negative" if hi < 0 else "inconclusive"


def compare(treated: list[Person], holdout: list[Person]) -> dict[str, Any]:
    nt, nh = len(treated), len(holdout)
    kt, kh = sum(p.bought for p in treated), sum(p.bought for p in holdout)
    rate_d, rate_lo, rate_hi = newcombe_diff(kt, nt, kh, nh)
    rev_d, rev_lo, rev_hi = bootstrap_diff(
        [p.revenue for p in treated], [p.revenue for p in holdout]
    )
    pro_d, pro_lo, pro_hi = bootstrap_diff([p.profit for p in treated], [p.profit for p in holdout])
    warnings = []
    if nh < MIN_PER_GROUP or nt < MIN_PER_GROUP:
        warnings.append(
            f"Only {nt} messaged and {nh} held back. Groups under {MIN_PER_GROUP} give very wide ranges; treat this as a first look."
        )
    if nh == 0:
        warnings.append(
            "There was no holdout group, so the effect cannot be separated from what would have happened anyway."
        )
    return {
        "treated": {"customers": nt, "bought": kt, "rate": kt / nt if nt else 0.0, "revenue_per_customer": float(np.mean([p.revenue for p in treated])) if nt else 0.0, "profit_per_customer": float(np.mean([p.profit for p in treated])) if nt else 0.0},
        "holdout": {"customers": nh, "bought": kh, "rate": kh / nh if nh else 0.0, "revenue_per_customer": float(np.mean([p.revenue for p in holdout])) if nh else 0.0, "profit_per_customer": float(np.mean([p.profit for p in holdout])) if nh else 0.0},
        "purchase_rate": {"diff_points": rate_d * 100, "low": rate_lo * 100, "high": rate_hi * 100, "verdict": verdict(rate_lo, rate_hi) if nh else "inconclusive"},
        "revenue": {"diff_per_customer": rev_d, "low": rev_lo, "high": rev_hi, "incremental_total": rev_d * nt, "incremental_low": rev_lo * nt, "incremental_high": rev_hi * nt},
        "profit": {"diff_per_customer": pro_d, "low": pro_lo, "high": pro_hi, "incremental_total": pro_d * nt, "incremental_low": pro_lo * nt, "incremental_high": pro_hi * nt, "verdict": verdict(pro_lo, pro_hi) if nh else "inconclusive"},
        "needed_per_group_for_5_points": needed_per_group(kh / nh if nh else 0.1),
        "warnings": warnings,
        "caveat": "Profit is after discounts. A holdout chosen the same way as the messaged group makes this a fair comparison; people who bought for other reasons are in both groups.",
    }  # fmt: skip
