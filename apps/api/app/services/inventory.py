"""Stock cover, reorder advice, dead stock and cash tied up, from stock snapshots and the forecast.

How the numbers work (docs/research/INVENTORY.md):
- Stock today = the latest snapshot minus the units sold since its date (never below zero).
- Days of cover = how long that stock lasts against the forecast (p50 per day). Beyond the 14-day
  forecast the daily rate is held flat, and the row says so.
- A product is *urgent* when it runs out before a new order could arrive (cover below lead time),
  and *reorder* when it would run out before the next order after this one could arrive
  (cover at most lead time plus the review period).
- The suggested quantity covers lead time plus review period at a demand level between the
  median and the p90 forecast (``service`` = 0 is lean, 1 is cautious), rounded up to the pack size.
"""

import csv
import io
import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.commerce import Order, OrderItem, OrderStatus, Product
from app.models.forecast import ForecastSeries
from app.models.inventory import InventorySetting, StockSnapshot
from app.models.workspace import Workspace
from app.services import costs
from app.services.analytics import queries as q
from app.services.forecasting import service as forecast_service

D = Decimal
DEFAULT_LEAD = 3
DEFAULT_SAFETY = 2
DEFAULT_REVIEW = 7
OVERSTOCK_DAYS = 45
DEAD_DAYS = 30
HORIZON_CAP = 60  # cover beyond this is reported as "60+"
MAX_IMPORT_ROWS = 50_000


class BadFileError(AppError):
    status_code = 422
    code = "bad_stock_file"


SYNONYMS = {
    "sku": ("sku", "item code", "code", "product code", "item id", "product id", "barcode"),
    "on_hand": ("on hand", "on_hand", "stock", "current stock", "closing stock", "quantity", "qty", "balance"),
    "date": ("date", "as of", "as_of", "stock date"),
    "lead": ("lead time", "lead_time", "lead days", "lead_time_days"),
    "pack": ("pack size", "pack", "moq", "min order", "case size"),
}  # fmt: skip


def _norm(h: str) -> str:
    return " ".join(h.strip().lower().replace("_", " ").replace("-", " ").split())


def _map_headers(headers: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    normed = {_norm(h): h for h in headers}
    for field, syns in SYNONYMS.items():
        for s in syns:
            if _norm(s) in normed:
                out[field] = normed[_norm(s)]
                break
    return out


def _dec(x: str) -> Decimal | None:
    try:
        v = D(x.replace(",", "").strip())
    except Exception:
        return None
    return v if v.is_finite() else None


# ------------------------------------------------------------------ pure planning


@dataclass(slots=True)
class Plan:
    cover_days: Decimal | None  # None means no demand, so stock never runs out
    status: str
    order_qty: Decimal
    reason: str


def cover(on_hand: Decimal, daily: list[Decimal], rate_after: Decimal) -> Decimal | None:
    """Days until ``on_hand`` is used up, walking the daily forecast, then a flat rate."""
    if on_hand <= 0:
        return ZERO_D
    left, day = on_hand, 0
    for d in daily:
        if d >= left:
            return D(day) + (left / d if d > 0 else ZERO_D)
        left -= d
        day += 1
    if rate_after <= 0:
        return None
    extra = left / rate_after
    return min(D(day) + extra, D(HORIZON_CAP + 1))


ZERO_D = D(0)


def plan(
    on_hand: Decimal,
    p50: list[Decimal],
    p90: list[Decimal],
    *,
    lead: int,
    review: int,
    pack: Decimal,
    service: Decimal,
    sold_last_30: Decimal,
) -> Plan:
    """Decide the status and order quantity for one product."""
    days = [p50[i] if i < len(p50) else p50[-1] if p50 else ZERO_D for i in range(HORIZON_CAP)]
    upper = [p90[i] if i < len(p90) else p90[-1] if p90 else ZERO_D for i in range(HORIZON_CAP)]
    rate_after = sum(p50, ZERO_D) / len(p50) if p50 else ZERO_D
    c = cover(on_hand, days[: len(p50)] if p50 else [], rate_after)
    if on_hand > 0 and sold_last_30 == 0 and rate_after <= D("0.05"):
        return Plan(
            c, "dead", ZERO_D, f"Nothing sold in {DEAD_DAYS} days, with stock on the shelf."
        )
    if c is None:
        return Plan(c, "ok", ZERO_D, "No demand expected, so it will not run out.")
    if sum(p50, ZERO_D) < D("0.5"):
        return Plan(c, "ok", ZERO_D, "Almost no demand expected, so nothing to order.")
    window = lead + review
    need = sum((days[i] + service * (upper[i] - days[i]) for i in range(window)), ZERO_D)
    raw = max(ZERO_D, need - on_hand)
    qty = (
        (raw / pack).to_integral_value(rounding="ROUND_CEILING") * pack
        if raw > 0 and pack > 0
        else raw
    )
    if c < lead:
        return Plan(
            c,
            "urgent",
            qty,
            f"Runs out in about {c:.0f} days, before an order placed today arrives ({lead} days).",
        )
    if c <= lead + review:
        return Plan(c, "reorder", qty, f"Lasts about {c:.0f} days; order now to avoid a gap.")
    if c > OVERSTOCK_DAYS:
        label = f"{HORIZON_CAP}+" if c > HORIZON_CAP else f"{c:.0f}"
        return Plan(c, "overstock", ZERO_D, f"{label} days of stock; more than needed.")
    return Plan(c, "ok", ZERO_D, f"Lasts about {c:.0f} days.")


# ------------------------------------------------------------------ import and edit


def parse_stock_file(
    content: bytes, default_date: date
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (rows, rejects). Each row has sku, on_hand and optional date, lead, pack."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BadFileError("The file must be a UTF-8 CSV.") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise BadFileError("The file is empty.")
    m = _map_headers(list(reader.fieldnames))
    if "sku" not in m or "on_hand" not in m:
        raise BadFileError(
            "The file needs a product code column (SKU or Item Code) and a stock column (Stock or Quantity)."
        )
    rows: dict[tuple[str, date], dict[str, Any]] = {}
    rejects: list[dict[str, Any]] = []
    for n, rec in enumerate(reader, start=2):
        if n - 1 > MAX_IMPORT_ROWS:
            raise BadFileError(f"Too many rows (limit {MAX_IMPORT_ROWS}).")
        sku = (rec.get(m["sku"]) or "").strip()
        qty = _dec(rec.get(m["on_hand"]) or "")
        if not sku:
            rejects.append({"row": n, "reason": "No product code"})
            continue
        if qty is None or qty < 0:
            rejects.append(
                {"row": n, "sku": sku, "reason": "Stock must be a number of zero or more"}
            )
            continue
        when = default_date
        if "date" in m and (rec.get(m["date"]) or "").strip():
            raw = rec[m["date"]].strip()
            try:
                when = (
                    datetime.strptime(raw, "%d/%m/%Y").date()
                    if "/" in raw
                    else date.fromisoformat(raw)
                )
            except ValueError:
                rejects.append(
                    {
                        "row": n,
                        "sku": sku,
                        "reason": f"Date '{raw}' not understood (use DD/MM/YYYY or YYYY-MM-DD)",
                    }
                )
                continue
        row: dict[str, Any] = {"sku": sku, "on_hand": qty, "date": when}
        if "lead" in m and (rec.get(m["lead"]) or "").strip():
            lead = _dec(rec[m["lead"]])
            if lead is None or lead < 0 or lead > 90:
                rejects.append({"row": n, "sku": sku, "reason": "Lead time must be 0 to 90 days"})
                continue
            row["lead"] = int(lead)
        if "pack" in m and (rec.get(m["pack"]) or "").strip():
            pack = _dec(rec[m["pack"]])
            if pack is None or pack <= 0:
                rejects.append({"row": n, "sku": sku, "reason": "Pack size must be above zero"})
                continue
            row["pack"] = pack
        rows[(sku, when)] = row  # the last row for a product and date wins
    return list(rows.values()), rejects


def _product_by_sku(db: Session, ws: uuid.UUID) -> dict[str, Product]:
    return {p.sku: p for p in db.scalars(select(Product).where(Product.workspace_id == ws))}


def _setting(db: Session, ws: uuid.UUID, product_id: uuid.UUID) -> InventorySetting:
    s = db.scalars(
        select(InventorySetting).where(InventorySetting.product_id == product_id)
    ).first()
    if s is None:
        s = InventorySetting(
            workspace_id=ws,
            product_id=product_id,
            lead_time_days=DEFAULT_LEAD,
            safety_days=DEFAULT_SAFETY,
            pack_size=D(1),
        )
        db.add(s)
    return s


def _put_snapshot(
    db: Session, ws: uuid.UUID, product_id: uuid.UUID, when: date, qty: Decimal
) -> None:
    snap = db.scalars(
        select(StockSnapshot).where(
            StockSnapshot.product_id == product_id, StockSnapshot.as_of == when
        )
    ).first()
    if snap is None:
        db.add(StockSnapshot(workspace_id=ws, product_id=product_id, as_of=when, on_hand=qty))
    else:
        snap.on_hand = qty


def import_stock(db: Session, ws: uuid.UUID, content: bytes, default_date: date) -> dict[str, Any]:
    rows, rejects = parse_stock_file(content, default_date)
    products = _product_by_sku(db, ws)
    imported, unmatched = 0, []
    for r in rows:
        p = products.get(r["sku"])
        if p is None:
            unmatched.append(r["sku"])
            continue
        _put_snapshot(db, ws, p.id, r["date"], r["on_hand"])
        if "lead" in r or "pack" in r:
            s = _setting(db, ws, p.id)
            if "lead" in r:
                s.lead_time_days = r["lead"]
            if "pack" in r:
                s.pack_size = r["pack"]
        imported += 1
    db.commit()
    return {
        "imported": imported,
        "unmatched_skus": sorted(set(unmatched))[:50],
        "unmatched": len(set(unmatched)),
        "rejected": rejects[:50],
        "rejected_count": len(rejects),
    }


def update_item(
    db: Session, ws: uuid.UUID, sku: str, *, on_hand: Decimal | None, as_of: date | None,
    lead_time_days: int | None, pack_size: Decimal | None, safety_days: int | None,
) -> None:  # fmt: skip
    p = _product_by_sku(db, ws).get(sku)
    if p is None:
        raise NotFoundError("Product not found")
    if on_hand is not None:
        _put_snapshot(db, ws, p.id, as_of or datetime.now(UTC).date(), on_hand)
    if lead_time_days is not None or pack_size is not None or safety_days is not None:
        s = _setting(db, ws, p.id)
        if lead_time_days is not None:
            s.lead_time_days = lead_time_days
        if pack_size is not None:
            s.pack_size = pack_size
        if safety_days is not None:
            s.safety_days = safety_days
    db.commit()


# ------------------------------------------------------------------ overview


def _daily_sales(
    db: Session, ws: uuid.UUID, start: date, end: date
) -> dict[str, dict[date, Decimal]]:
    stmt = (
        select(Product.sku, Order.business_date, func.sum(OrderItem.quantity))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .where(OrderItem.workspace_id == ws, Order.workspace_id == ws, Order.status == OrderStatus.COMPLETED,
               Order.business_date >= start, Order.business_date <= end)
        .group_by(Product.sku, Order.business_date)
    )  # fmt: skip
    out: dict[str, dict[date, Decimal]] = defaultdict(dict)
    for sku, day, qty in db.execute(stmt):
        out[sku][day] = D(str(qty))
    return out


def overview(
    db: Session,
    workspace: Workspace,
    *,
    service: Decimal = D("0.5"),
    review_days: int = DEFAULT_REVIEW,
) -> dict[str, Any]:
    ws = workspace.id
    _, last = q.workspace_bounds(db, ws)
    if last is None:
        return {"as_of": None, "items": [], "summary": _summary([], 0), "has_forecast": False}
    products = _product_by_sku(db, ws)
    snaps: dict[uuid.UUID, StockSnapshot] = {}
    for s in db.scalars(
        select(StockSnapshot).where(StockSnapshot.workspace_id == ws).order_by(StockSnapshot.as_of)
    ):
        snaps[s.product_id] = s  # ascending, so the newest wins
    settings = {
        s.product_id: s
        for s in db.scalars(select(InventorySetting).where(InventorySetting.workspace_id == ws))
    }
    run = forecast_service.latest_run(db, ws)
    series: dict[str, ForecastSeries] = {}
    if run is not None:
        series = {
            s.sku: s
            for s in db.scalars(select(ForecastSeries).where(ForecastSeries.run_id == run.id))
        }
    sales = _daily_sales(db, ws, last - timedelta(days=89), last)
    cost_by_sku = {i["sku"]: i.get("cost_now") for i in costs.overview(db, ws, last)["items"]}

    items: list[dict[str, Any]] = []
    for sku, p in products.items():
        snap = snaps.get(p.id)
        if snap is None:
            continue
        st = settings.get(p.id)
        lead = st.lead_time_days if st else DEFAULT_LEAD
        pack = st.pack_size if st else D(1)
        per_day = sales.get(sku, {})
        sold_since = sum((u for d, u in per_day.items() if d > snap.as_of), ZERO_D)
        on_hand_now = max(ZERO_D, snap.on_hand - sold_since)
        sold_30 = sum(
            (u for d, u in per_day.items() if d > last - timedelta(days=DEAD_DAYS)), ZERO_D
        )
        fs = series.get(sku)
        extended = False
        if fs is not None and fs.data.get("p50"):
            p50 = [D(str(v)) for v in fs.data["p50"]]
            p90 = [D(str(v)) for v in fs.data["p90"]]
            extended = True
        else:  # no forecast for this product: use its recent daily rate
            rate = (
                sum((u for d, u in per_day.items() if d > last - timedelta(days=28)), ZERO_D) / 28
            )
            p50, p90 = [rate] * 14, [rate * D("1.3")] * 14
        pl = plan(
            on_hand_now,
            p50,
            p90,
            lead=lead,
            review=review_days,
            pack=pack,
            service=service,
            sold_last_30=sold_30,
        )
        cost = cost_by_sku.get(sku) or p.unit_cost
        daily = sum(p50, ZERO_D) / len(p50) if p50 else ZERO_D
        excess_units = (
            max(ZERO_D, on_hand_now - daily * OVERSTOCK_DAYS)
            if pl.status in ("overstock", "dead")
            else ZERO_D
        )
        items.append(
            {
                "sku": sku, "name": p.name, "category": p.category,
                "snapshot_date": snap.as_of, "snapshot_on_hand": snap.on_hand, "sold_since": sold_since,
                "on_hand": on_hand_now, "daily_rate": daily.quantize(D("0.01"), rounding=ROUND_HALF_UP),
                "cover_days": None if pl.cover_days is None else pl.cover_days.quantize(D("0.1"), rounding=ROUND_HALF_UP),
                "run_out_date": None if pl.cover_days is None or pl.cover_days > HORIZON_CAP else last + timedelta(days=math.floor(pl.cover_days)),
                "lead_time_days": lead, "pack_size": pack, "status": pl.status, "reason": pl.reason,
                "order_qty": pl.order_qty, "unit_cost": None if cost is None else D(str(cost)),
                "order_cost": None if cost is None else (pl.order_qty * D(str(cost))).quantize(D("0.01")),
                "cash_tied": None if cost is None else (on_hand_now * D(str(cost))).quantize(D("0.01")),
                "excess_cash": None if cost is None else (excess_units * D(str(cost))).quantize(D("0.01")),
                "forecast_based": extended,
            }
        )  # fmt: skip
    rank = {"urgent": 0, "reorder": 1, "dead": 2, "overstock": 3, "ok": 4}
    items.sort(
        key=lambda i: (
            rank[i["status"]],
            i["cover_days"] if i["cover_days"] is not None else D(9999),
        )
    )
    sold_skus = {s for s, d in sales.items() if any(day > last - timedelta(days=28) for day in d)}
    missing = len([s for s in sold_skus if s in products and products[s].id not in snaps])
    return {
        "as_of": last,
        "items": items,
        "summary": _summary(items, missing),
        "has_forecast": run is not None,
        "service": service,
        "review_days": review_days,
    }


def _summary(items: list[dict[str, Any]], missing: int) -> dict[str, Any]:
    def total(key: str, status: str | None = None) -> Decimal:
        return sum(
            (
                i[key]
                for i in items
                if i[key] is not None and (status is None or i["status"] == status)
            ),
            ZERO_D,
        )

    return {
        "tracked": len(items),
        "urgent": sum(1 for i in items if i["status"] == "urgent"),
        "reorder": sum(1 for i in items if i["status"] == "reorder"),
        "overstock": sum(1 for i in items if i["status"] == "overstock"),
        "dead": sum(1 for i in items if i["status"] == "dead"),
        "missing_stock": missing,
        "cash_tied": total("cash_tied"),
        "excess_cash": total("excess_cash"),
        "dead_cash": total("cash_tied", "dead"),
        "order_cost": total("order_cost"),
    }


def order_list_csv(items: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "sku",
            "product",
            "status",
            "on_hand",
            "cover_days",
            "lead_time_days",
            "order_qty",
            "estimated_cost",
            "why",
        ]
    )
    for i in items:
        if i["order_qty"] > 0:
            w.writerow(
                [
                    i["sku"],
                    i["name"],
                    i["status"],
                    i["on_hand"],
                    i["cover_days"],
                    i["lead_time_days"],
                    i["order_qty"],
                    i["order_cost"] if i["order_cost"] is not None else "",
                    i["reason"],
                ]
            )
    return buf.getvalue()
