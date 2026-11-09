"""Synthetic two-year retail demand with *known* structure, so model choices can be judged.

Each SKU gets a base level, weekly shape, yearly shape, trend, promotions that lift demand, a few
stock-out spells (recorded as zeros) and Poisson noise. Intermittent SKUs have a low base level.
Standard library only; the seed is fixed so every run sees the same data.
"""

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
START = date(2024, 11, 10)
DAYS = 730
OUT = Path(__file__).resolve().parent / "out"

# kind: fast (smooth), mid, slow (intermittent), lumpy
SKUS: list[tuple[str, str, float, float]] = []  # sku, kind, base units/day, price
_KINDS = [("fast", 28.0), ("fast", 18.0), ("mid", 9.0), ("mid", 6.0), ("slow", 1.2), ("slow", 0.6)]

FESTIVE_PEAKS = [date(2024, 11, 1), date(2025, 10, 20), date(2026, 11, 8)]  # moves each year
WEEKDAY = [0.88, 0.85, 0.9, 0.95, 1.05, 1.32, 1.25]


def poisson(rnd: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam > 40:
        return max(0, round(rnd.gauss(lam, math.sqrt(lam))))
    limit, k, p = math.exp(-lam), 0, 1.0
    while p > limit:
        k += 1
        p *= rnd.random()
    return k - 1


def festive(d: date) -> float:
    return 1.0 + max(
        (0.55 * math.exp(-(((d - p).days / 9) ** 2)) for p in FESTIVE_PEAKS), default=0.0
    )


def yearly(d: date) -> float:
    doy = d.timetuple().tm_yday
    summer = 1.0 + 0.12 * math.sin(2 * math.pi * (doy - 100) / 365)
    return summer * festive(d)


def generate(n_skus: int = 40) -> list[dict[str, str]]:
    rnd = random.Random(SEED)
    rows: list[dict[str, str]] = []
    for i in range(n_skus):
        kind, base = _KINDS[i % len(_KINDS)]
        base *= rnd.uniform(0.7, 1.3)
        price = rnd.choice([28, 45, 60, 99, 135, 185, 240, 295])
        trend = rnd.uniform(-0.0003, 0.0009)  # per day, compounding
        weekly_strength = 0.2 if kind == "slow" else 1.0
        sku = f"SKU-{i + 1:03d}"
        promo_until, promo_depth = -1, 0.0
        stock_until = -1
        for t in range(DAYS):
            d = START + timedelta(days=t)
            if t > promo_until and rnd.random() < 0.012:  # a 3-7 day promotion
                promo_until, promo_depth = t + rnd.randint(3, 7), rnd.choice([0.05, 0.10, 0.15])
            on_promo = t <= promo_until
            if t > stock_until and kind != "slow" and rnd.random() < 0.004:  # stock-out spell
                stock_until = t + rnd.randint(2, 6)
            out_of_stock = t <= stock_until
            lift = 1 + 3.0 * promo_depth if on_promo else 1.0
            week = 1 + (WEEKDAY[d.weekday()] - 1) * weekly_strength
            mean = base * (1 + trend) ** t * week * yearly(d) * lift
            if kind == "mid":
                mean *= rnd.uniform(0.85, 1.15)
            units = 0 if out_of_stock else poisson(rnd, mean)
            if kind == "slow" and units and rnd.random() < 0.15:
                units *= rnd.randint(2, 4)  # occasional bulk buy -> lumpy
            rows.append(
                {
                    "sku": sku,
                    "kind": kind,
                    "date": d.isoformat(),
                    "units": str(units),
                    "price": str(price),
                    "discount_rate": f"{promo_depth if on_promo else 0.0:.2f}",
                    "stockout": "1" if out_of_stock else "0",
                }
            )
    return rows


def write(path: Path | None = None) -> Path:
    OUT.mkdir(exist_ok=True)
    path = path or OUT / "panel.csv"
    rows = generate()
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


if __name__ == "__main__":
    p = write()
    print(f"wrote {p}")
