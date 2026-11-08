"""Generate a realistic, reproducible demo sales export for Vyapar AI.

    python scripts/generate_demo_data.py            # writes data/sample/*.csv

Outputs (one row per order line, headers styled like a billing-tool export):
  - vyapar_demo_sales.csv        clean data, ~90 days, a single multi-category store
  - vyapar_demo_sales_messy.csv  the same plus ~2% deliberately broken rows (bad dates,
                                 missing SKUs, negative quantities, text in numbers) to exercise
                                 validation

Only the standard library is used. The random seed is fixed, so the files are identical on
every run and tests can rely on their totals.
"""

import csv
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

SEED = 20261108
OUT = Path(__file__).resolve().parents[1] / "data" / "sample"

# sku, name, category, list price, cost, popularity weight
CATALOGUE = [
    ("ATT-5KG", "Wheat Atta 5 kg", "Staples", 295, 248, 9),
    ("RIC-5KG", "Basmati Rice 5 kg", "Staples", 520, 430, 6),
    ("TUR-1KG", "Toor Dal 1 kg", "Staples", 165, 138, 7),
    ("SUG-1KG", "Sugar 1 kg", "Staples", 48, 41, 8),
    ("SAL-1KG", "Iodised Salt 1 kg", "Staples", 28, 21, 6),
    ("OIL-1L", "Mustard Oil 1 L", "Staples", 185, 158, 6),
    ("GHE-1L", "Desi Ghee 1 L", "Dairy", 645, 560, 4),
    ("MLK-500", "Toned Milk 500 ml", "Dairy", 29, 25, 10),
    ("PAN-200", "Paneer 200 g", "Dairy", 95, 78, 4),
    ("TEA-500", "Tea 500 g", "Beverages", 240, 196, 5),
    ("COF-100", "Instant Coffee 100 g", "Beverages", 310, 262, 2),
    ("BIS-FAM", "Biscuits Family Pack", "Snacks", 60, 47, 7),
    ("NAM-400", "Namkeen 400 g", "Snacks", 110, 86, 5),
    ("NOO-4PK", "Noodles Pack of 4", "Snacks", 56, 44, 6),
    ("SOP-4PK", "Bath Soap 4 x 100 g", "Personal care", 160, 128, 4),
    ("SHA-340", "Shampoo 340 ml", "Personal care", 275, 221, 3),
    ("DET-1KG", "Detergent 1 kg", "Household", 135, 108, 4),
    ("DSW-500", "Dishwash Gel 500 ml", "Household", 99, 77, 3),
    ("MOO-1KG", "Moong Dal 1 kg", "Staples", 150, 126, 5),
    ("CHA-1KG", "Chana Dal 1 kg", "Staples", 120, 99, 5),
    ("JAG-1KG", "Jaggery 1 kg", "Staples", 62, 50, 3),
    ("POH-500", "Poha 500 g", "Staples", 45, 36, 4),
    ("RAV-500", "Rava 500 g", "Staples", 38, 30, 3),
    ("BES-500", "Besan 500 g", "Staples", 68, 55, 3),
    ("SFO-1L", "Sunflower Oil 1 L", "Staples", 142, 124, 6),
    ("BUT-100", "Butter 100 g", "Dairy", 58, 50, 4),
    ("CUR-400", "Curd 400 g", "Dairy", 38, 31, 6),
    ("EGG-12", "Eggs Tray of 12", "Dairy", 84, 72, 6),
    ("CHE-200", "Cheese Slices 200 g", "Dairy", 135, 111, 2),
    ("TEB-25", "Tea Bags 25 pack", "Beverages", 120, 94, 3),
    ("JUI-1L", "Fruit Juice 1 L", "Beverages", 110, 84, 3),
    ("SOD-750", "Soft Drink 750 ml", "Beverages", 40, 31, 7),
    ("CHI-52", "Potato Chips 52 g", "Snacks", 20, 15, 9),
    ("CHO-BAR", "Chocolate Bar", "Snacks", 40, 31, 7),
    ("RUS-200", "Rusk 200 g", "Snacks", 35, 27, 4),
    ("TOO-150", "Toothpaste 150 g", "Personal care", 105, 82, 5),
    ("HOI-200", "Hair Oil 200 ml", "Personal care", 118, 92, 3),
    ("FAC-100", "Face Wash 100 ml", "Personal care", 185, 140, 2),
    ("FLO-1L", "Floor Cleaner 1 L", "Household", 175, 138, 3),
    ("AGA-20", "Incense Sticks 20 pack", "Household", 30, 22, 4),
]

# Supplier price changes: (sku, first day the new cost applies, multiplier). Real shops see their
# cost move like this, so margins are computed from the cost on each bill, not one fixed number.
COST_CHANGES = [
    ("OIL-1L", date(2026, 9, 10), 1.07),
    ("SFO-1L", date(2026, 9, 10), 1.09),
    ("SUG-1KG", date(2026, 10, 5), 1.06),
    ("TUR-1KG", date(2026, 10, 1), 1.05),
    ("GHE-1L", date(2026, 9, 20), 0.97),
    ("EGG-12", date(2026, 10, 12), 1.08),
]


def cost_on(sku: str, base: int, day: date) -> float:
    cost = float(base)
    for k, since, mult in COST_CHANGES:
        if k == sku and day >= since:
            cost *= mult
    return round(cost, 2)
CITIES = [("Maharashtra", "Pune"), ("Maharashtra", "Pune"), ("Maharashtra", "Pimpri"), ("Maharashtra", "Hadapsar")]
CHANNELS = ["Store", "Store", "Store", "Phone order", "WhatsApp"]


def money(x: float | Decimal) -> str:
    return str(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def generate() -> list[dict[str, str]]:
    rnd = random.Random(SEED)
    start = date(2026, 8, 1)
    customers = [f"C-{1000 + i}" for i in range(320)]
    rows: list[dict[str, str]] = []
    bill = 4000
    for d in range(92):
        day = start + timedelta(days=d)
        weekday_boost = [0.9, 0.85, 0.9, 0.95, 1.05, 1.3, 1.25][day.weekday()]
        month_end = 1.15 if day.day >= 28 or day.day <= 2 else 1.0
        n_bills = int(rnd.gauss(34, 5) * weekday_boost * month_end)
        for _ in range(max(n_bills, 10)):
            bill += 1
            cust = rnd.choice(customers) if rnd.random() < 0.72 else ""  # walk-ins have no customer
            state, city = rnd.choice(CITIES)
            channel = rnd.choice(CHANNELS)
            status = "Paid" if rnd.random() > 0.03 else "Cancelled"
            hour = rnd.randint(8, 21)
            minute = rnd.randint(0, 59)
            n_items = rnd.choices([1, 2, 3, 4, 5], [3, 4, 3, 2, 1])[0]
            for item in rnd.sample(range(len(CATALOGUE)), k=n_items):
                sku, name, cat, price, cost, _w = CATALOGUE[item]
                qty = rnd.choices([1, 2, 3, 4], [6, 3, 1, 0.5])[0]
                disc = money(price * qty * 0.05) if rnd.random() < 0.12 else "0.00"
                gst = money((price * qty - float(disc)) * (0.05 if cat in ("Staples", "Dairy") else 0.18) / 1.0)
                rows.append(
                    {
                        "Bill No": f"INV-{bill}",
                        "Bill Date": f"{day.strftime('%d/%m/%Y')} {hour:02d}:{minute:02d}",
                        "Item Code": sku,
                        "Item Name": name,
                        "Category": cat,
                        "Qty": str(qty),
                        "Rate": money(price),
                        "Discount": disc,
                        "Cost": money(cost_on(sku, cost, day)),
                        "Customer": cust,
                        "State": state if cust else "",
                        "City": city if cust else "",
                        "Channel": channel,
                        "Status": status,
                        "GST": gst,
                    }
                )
    return rows


def make_messy(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rnd = random.Random(SEED + 1)
    messy = [dict(r) for r in rows]
    breakers = [
        lambda r: r.update({"Bill Date": "31/02/2026"}),
        lambda r: r.update({"Item Code": ""}),
        lambda r: r.update({"Qty": "-1"}),
        lambda r: r.update({"Rate": "N/A"}),
        lambda r: r.update({"Status": "lost in transit"}),
    ]
    for r in rnd.sample(messy, k=max(5, len(messy) // 50)):
        rnd.choice(breakers)(r)
    return messy


def write(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    rows = generate()
    write(OUT / "vyapar_demo_sales.csv", rows)
    write(OUT / "vyapar_demo_sales_messy.csv", make_messy(rows))
    bills = len({r["Bill No"] for r in rows})
    print(f"Wrote {len(rows):,} lines across {bills:,} bills to {OUT}")


if __name__ == "__main__":
    main()
