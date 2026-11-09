"""The modelling panel: one row per (product, business day), zero-filled, from completed orders."""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from numpy.typing import NDArray
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.commerce import OrderItem, Product
from app.services.analytics.queries import LINE_GROSS, LINE_NET, _lines, workspace_bounds
from app.services.analytics.types import Filters
from app.services.forecasting.demand import stockout_suspects

Arr = NDArray[np.float64]
MAX_DAYS = 730
MIN_SKU_SALES = 3  # products with fewer sale days are left out (nothing to learn from)


@dataclass(slots=True)
class Panel:
    skus: list[str]
    names: list[str]
    categories: list[str | None]
    dates: list[date]
    y: Arr  # units, shape (series, days)
    disc: Arr  # discount rate on each day, 0..1
    stockout: NDArray[np.bool_]  # suspected stock-out days (zeros that are not real demand)
    net_per_unit: Arr  # average net sales per unit over the last 28 days

    @property
    def n_days(self) -> int:
        return len(self.dates)


def clean(y: Arr, stockout: NDArray[np.bool_]) -> Arr:
    """Replace stock-out days with the recent same-weekday level so models do not learn zeros."""
    out = y.copy()
    for t in np.flatnonzero(stockout):
        prev = [out[t - 7 * k] for k in range(1, 5) if t - 7 * k >= 0 and not stockout[t - 7 * k]]
        if prev:
            out[t] = float(np.mean(prev))
        else:
            lo = max(0, int(t) - 28)
            window = y[lo : int(t)][~stockout[lo : int(t)]]
            out[t] = float(window.mean()) if len(window) else 0.0
    return out


def _f(x: object) -> float:
    return float(x) if isinstance(x, int | float | Decimal) else 0.0


def load_panel(db: Session, ws: uuid.UUID, as_of: date | None = None) -> Panel | None:
    first, last = workspace_bounds(db, ws)
    if last is None or first is None:
        return None
    last = min(last, as_of) if as_of else last
    first = max(first, last - timedelta(days=MAX_DAYS - 1))
    flt = Filters(date_from=first, date_to=last)
    from app.models.commerce import Order  # local import keeps the module header small

    stmt = _lines(
        [
            Product.sku,
            Product.name,
            Product.category,
            Order.business_date,
            func.sum(OrderItem.quantity),
            func.sum(OrderItem.discount_amount),
            func.sum(LINE_GROSS),
            func.sum(LINE_NET),
        ],
        ws,
        flt,
    ).group_by(Product.sku, Product.name, Product.category, Order.business_date)
    rows = db.execute(stmt).all()
    if not rows:
        return None

    days = (last - first).days + 1
    index: dict[str, int] = {}
    meta: list[tuple[str, str | None]] = []
    for r in rows:
        if r[0] not in index:
            index[r[0]] = len(index)
            meta.append((r[1], r[2]))
    n = len(index)
    y = np.zeros((n, days))
    gross = np.zeros((n, days))
    disc = np.zeros((n, days))
    net = np.zeros((n, days))
    for sku, _name, _cat, day, qty, dsc, grs, nt in rows:
        i, t = index[sku], (day - first).days
        y[i, t], disc[i, t], gross[i, t], net[i, t] = _f(qty), _f(dsc), _f(grs), _f(nt)
    rate = np.divide(disc, gross, out=np.zeros_like(disc), where=gross > 0)

    keep = [i for i in range(n) if (y[i] > 0).sum() >= MIN_SKU_SALES]
    skus = [s for s, _ in sorted(index.items(), key=lambda kv: kv[1])]
    y, rate, net = y[keep], rate[keep], net[keep]
    tail_units = y[:, -28:].sum(axis=1)
    tail_net = net[:, -28:].sum(axis=1)
    all_units = y.sum(axis=1)
    all_net = net.sum(axis=1)
    npu = np.where(
        tail_units > 0,
        tail_net / np.maximum(tail_units, 1e-9),
        all_net / np.maximum(all_units, 1e-9),
    )

    stock = np.zeros_like(y, dtype=bool)
    for i in range(len(keep)):
        if (y[i] > 0).mean() >= 0.6:  # only fast movers: zeros on slow movers are normal
            for start, length in stockout_suspects(list(y[i]), min_run=5):
                stock[i, start : start + length] = True
    return Panel(
        skus=[skus[i] for i in keep],
        names=[meta[i][0] for i in keep],
        categories=[meta[i][1] for i in keep],
        dates=[first + timedelta(days=d) for d in range(days)],
        y=y,
        disc=rate,
        stockout=stock,
        net_per_unit=npu,
    )
