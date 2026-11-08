"""Inspection, validation and import of an uploaded commerce file.

Validation is the single source of truth: the import re-runs it, so a file that changed on disk
or a mapping that changed after validation can never import unchecked rows.
"""

import uuid
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.commerce import Customer, Order, OrderItem, OrderStatus, Product
from app.services.ingestion.fields import FIELD_BY_KEY, FIELDS, REQUIRED, suggest_mapping
from app.services.ingestion.parsing import ParseError, parse_date, parse_number, parse_status
from app.services.ingestion.reader import FileTooLargeError, UnsupportedFileError, read_table


class MappingError(AppError):
    status_code = 422
    code = "invalid_mapping"


MAX_SAMPLE_ERRORS = 200
_CHUNK = 500


def clean_headers(headers: list[str]) -> list[str]:
    """Blank headers become 'Column N'; duplicates get a ' (2)' suffix so mapping is unambiguous."""
    seen: Counter[str] = Counter()
    out: list[str] = []
    for i, h in enumerate(headers):
        name = h.strip() or f"Column {i + 1}"
        seen[name] += 1
        out.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
    return out


def _as_text(v: Any) -> str:
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M") if (v.hour or v.minute) else v.strftime("%Y-%m-%d")
    return str(v)


# ---------------------------------------------------------------- inspection


def inspect_file(path: Path, file_type: str, max_rows: int) -> dict[str, Any]:
    raw_headers, rows = read_table(path, file_type)
    headers = clean_headers(raw_headers)
    if not any(raw_headers):
        raise UnsupportedFileError("The first row must contain column names")
    n = len(headers)
    non_empty = [0] * n
    numeric = [0] * n
    dates = [0] * n
    samples: list[list[str]] = [[] for _ in range(n)]
    sample_rows: list[list[str]] = []
    count = 0
    for row in rows:
        count += 1
        if count > max_rows:
            raise FileTooLargeError(f"The file has more than {max_rows:,} rows")
        if len(sample_rows) < 10:
            sample_rows.append([_as_text(c) for c in row[:n]])
        for i in range(n):
            v = row[i] if i < len(row) else ""
            if v == "" or v is None:
                continue
            non_empty[i] += 1
            if len(samples[i]) < 5:
                samples[i].append(_as_text(v))
            if count <= 500:
                try:
                    parse_number(v)
                    numeric[i] += 1
                except ParseError:
                    try:
                        parse_date(v)
                        dates[i] += 1
                    except ParseError:
                        pass
    if count == 0:
        raise UnsupportedFileError("The file has a header row but no data rows")

    checked = min(count, 500)
    columns = []
    for i, h in enumerate(headers):
        filled = non_empty[i]
        base = min(filled, checked) or 1
        inferred = (
            "number" if numeric[i] / base > 0.9 else "date" if dates[i] / base > 0.9 else "text"
        )
        columns.append(
            {
                "name": h,
                "inferred_type": inferred,
                "empty_pct": round(100 * (count - filled) / count, 1),
                "samples": samples[i],
            }
        )
    return {
        "row_count": count,
        "columns": columns,
        "sample_rows": sample_rows,
        "headers": headers,
        "suggested_mapping": suggest_mapping(headers),
        "fields": [
            {"key": f.key, "label": f.label, "required": f.required, "kind": f.kind} for f in FIELDS
        ],
    }


# ---------------------------------------------------------------- validation


@dataclass(slots=True)
class Line:
    row: int
    order_id: str
    order_date: datetime
    sku: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal
    unit_cost: Decimal | None
    category: str | None
    customer_id: str | None
    region: str | None
    city: str | None
    channel: str | None
    status: OrderStatus
    tax_amount: Decimal


@dataclass(slots=True)
class Validation:
    rows_total: int = 0
    lines: list[Line] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    error_rows: set[int] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        by_field = Counter(e["field"] for e in self.errors)
        valid = self.lines
        dates = [ln.order_date for ln in valid]
        completed = [ln for ln in valid if ln.status == OrderStatus.COMPLETED]
        net = sum((ln.quantity * ln.unit_price - ln.discount for ln in completed), Decimal("0"))
        return {
            "rows_total": self.rows_total,
            "rows_valid": len(valid),
            "rows_invalid": len(self.error_rows),
            "errors_by_field": dict(by_field),
            "sample_errors": self.errors[:MAX_SAMPLE_ERRORS],
            "error_count": len(self.errors),
            "warnings": self.warnings[:20],
            "preview": {
                "orders": len({ln.order_id for ln in valid}),
                "products": len({ln.sku for ln in valid}),
                "customers": len({ln.customer_id for ln in valid if ln.customer_id}),
                "date_from": min(dates).date().isoformat() if dates else None,
                "date_to": max(dates).date().isoformat() if dates else None,
                "net_sales_completed": str(net.quantize(Decimal("0.01"))),
            },
            "validated_at": datetime.now(UTC).isoformat(),
        }


def _num(
    raw: Any, key: str, required: bool, minimum: Decimal | None, errs: list[tuple[str, str]]
) -> Decimal | None:
    """Parse a numeric cell, appending a (field, message) error instead of raising."""
    if raw in ("", None):
        if required:
            errs.append((key, "is required"))
        return None
    try:
        d = parse_number(raw)
    except ParseError as exc:
        errs.append((key, str(exc)))
        return None
    if minimum is not None and d < minimum:
        errs.append((key, f"must be ≥ {minimum}"))
        return None
    return d


def validate_mapping(mapping: dict[str, Any], headers: list[str]) -> dict[str, str]:
    fields = mapping.get("fields") or {}
    if not isinstance(fields, dict):
        raise MappingError("Mapping must be an object of field → column")
    missing = [k for k in REQUIRED if not fields.get(k)]
    if missing:
        labels = ", ".join(FIELD_BY_KEY[k].label for k in missing)
        raise MappingError(f"Map the required fields first: {labels}")
    unknown_cols = [c for c in fields.values() if c and c not in headers]
    if unknown_cols:
        raise MappingError(f"Unknown columns in mapping: {', '.join(unknown_cols)}")
    unknown_fields = [k for k in fields if k not in FIELD_BY_KEY]
    if unknown_fields:
        raise MappingError(f"Unknown fields in mapping: {', '.join(unknown_fields)}")
    return {k: v for k, v in fields.items() if v}


def validate_file(path: Path, file_type: str, mapping: dict[str, Any], max_rows: int) -> Validation:
    raw_headers, rows = read_table(path, file_type)
    headers = clean_headers(raw_headers)
    fields = validate_mapping(mapping, headers)
    order = mapping.get("date_order", "dmy")
    if order not in ("dmy", "mdy", "ymd"):
        order = "dmy"
    idx = {k: headers.index(col) for k, col in fields.items()}
    latest_allowed = datetime.now(UTC) + timedelta(days=1)

    v = Validation()
    order_heads: dict[str, tuple[datetime, str | None, int]] = {}
    sku_names: dict[str, str] = {}

    def get(row: list[Any], key: str) -> Any:
        i = idx.get(key)
        return row[i] if i is not None and i < len(row) else ""

    def text(row: list[Any], key: str) -> str | None:
        val = get(row, key)
        s = _as_text(val).strip() if val not in ("", None) else ""
        return s or None

    for n, row in enumerate(rows, start=2):  # row 1 is the header
        v.rows_total += 1
        if v.rows_total > max_rows:
            raise FileTooLargeError(f"The file has more than {max_rows:,} rows")
        errs: list[tuple[str, str]] = []

        for key in ("order_id", "sku", "product_name"):
            if not text(row, key):
                errs.append((key, "is required"))

        qty = _num(get(row, "quantity"), "quantity", True, None, errs)
        if qty is not None and qty <= 0:
            errs.append(("quantity", "must be greater than 0 (returns are not supported yet)"))
            qty = None
        zero = Decimal("0")
        price = _num(get(row, "unit_price"), "unit_price", True, zero, errs)
        discount = _num(get(row, "discount"), "discount", False, zero, errs) or zero
        cost = _num(get(row, "unit_cost"), "unit_cost", False, zero, errs)
        tax = _num(get(row, "tax_amount"), "tax_amount", False, zero, errs) or zero

        when: datetime | None = None
        raw_date = get(row, "order_date")
        if raw_date in ("", None):
            errs.append(("order_date", "is required"))
        else:
            try:
                when = parse_date(raw_date, order)
                if when > latest_allowed:
                    errs.append(("order_date", "is in the future"))
                    when = None
            except ParseError as exc:
                errs.append(("order_date", str(exc)))

        status = OrderStatus.COMPLETED
        if "status" in idx:
            try:
                status = parse_status(get(row, "status"))
            except ParseError as exc:
                errs.append(("status", str(exc)))

        if qty is not None and price is not None and discount > qty * price:
            errs.append(("discount", "is larger than the line amount"))

        order_id = text(row, "order_id")
        customer = text(row, "customer_id")
        if order_id and when and not errs:
            head = order_heads.get(order_id)
            if head is None:
                order_heads[order_id] = (when, customer, n)
            else:
                if head[0].date() != when.date():
                    errs.append(("order_date", f"differs from row {head[2]} of the same order"))
                elif (head[1] or None) != (customer or None):
                    errs.append(("customer_id", f"differs from row {head[2]} of the same order"))

        if errs:
            v.error_rows.add(n)
            for f, msg in errs:
                col = fields.get(f, "")
                v.errors.append(
                    {
                        "row": n,
                        "field": f,
                        "column": col,
                        "message": msg,
                        "value": _as_text(get(row, f))[:80],
                    }
                )
            continue

        sku = text(row, "sku") or ""
        name = text(row, "product_name") or ""
        if sku in sku_names and sku_names[sku] != name and len(v.warnings) < 20:
            v.warnings.append(
                f"Row {n}: SKU {sku} has a different name than earlier rows; "
                "the first name is kept."
            )
        sku_names.setdefault(sku, name)

        if qty is None or price is None or when is None or not order_id:  # pragma: no cover
            continue  # unreachable: any of these being missing already produced an error above
        v.lines.append(
            Line(
                row=n,
                order_id=order_id,
                order_date=when,
                sku=sku,
                product_name=sku_names[sku],
                quantity=qty,
                unit_price=price,
                discount=discount,
                unit_cost=cost,
                category=text(row, "category"),
                customer_id=customer,
                region=text(row, "region"),
                city=text(row, "city"),
                channel=text(row, "channel"),
                status=status,
                tax_amount=tax,
            )
        )
    if v.rows_total == 0:
        raise UnsupportedFileError("The file has no data rows")
    return v


def iter_error_csv(validation: Validation) -> Iterator[str]:
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["row", "field", "column", "message", "value"])
    yield buf.getvalue()
    for e in validation.errors:
        buf.seek(0)
        buf.truncate()
        w.writerow([e["row"], e["field"], e["column"], e["message"], e["value"]])
        yield buf.getvalue()


# ---------------------------------------------------------------- import


@dataclass(slots=True)
class ImportResult:
    orders_created: int = 0
    lines_imported: int = 0
    products_created: int = 0
    customers_created: int = 0
    rows_rejected: int = 0
    duplicate_orders: int = 0


def _existing(
    db: Session, model: Any, column: Any, workspace_id: uuid.UUID, keys: set[str]
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    key_list = list(keys)
    for i in range(0, len(key_list), _CHUNK):
        chunk = key_list[i : i + _CHUNK]
        stmt = select(model).where(model.workspace_id == workspace_id, column.in_(chunk))
        for obj in db.scalars(stmt):
            out[getattr(obj, column.key)] = obj
    return out


def to_utc_and_business_date(wall: datetime, timezone: str) -> tuple[datetime, "date"]:
    """Treat a parsed wall-clock time as being in the workspace timezone.

    Returns the UTC instant to store and the business date (the shopkeeper's calendar day).
    """
    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    local = wall.replace(tzinfo=tz)
    return local.astimezone(UTC), wall.date()


def import_lines(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    dataset_id: uuid.UUID,
    currency: str,
    timezone: str = "Asia/Kolkata",
    validation: Validation,
) -> ImportResult:
    """Normalise validated lines into products, customers, orders and order items.

    Runs inside the caller's transaction; the caller commits or rolls back.
    Orders whose external key already exists in the workspace are skipped (idempotent re-import).
    """
    res = ImportResult(rows_rejected=len(validation.error_rows))
    lines = validation.lines
    existing_orders = _existing(
        db, Order, Order.external_key, workspace_id, {ln.order_id for ln in lines}
    )
    if existing_orders:
        dup = [ln for ln in lines if ln.order_id in existing_orders]
        res.duplicate_orders = len({ln.order_id for ln in dup})
        res.rows_rejected += len(dup)
        lines = [ln for ln in lines if ln.order_id not in existing_orders]

    products = _existing(db, Product, Product.sku, workspace_id, {ln.sku for ln in lines})
    for ln in lines:
        if ln.sku not in products:
            p = Product(
                workspace_id=workspace_id,
                sku=ln.sku,
                name=ln.product_name,
                category=ln.category,
                unit_cost=ln.unit_cost,
                list_price=ln.unit_price,
            )
            db.add(p)
            products[ln.sku] = p
            res.products_created += 1

    customer_keys = {ln.customer_id for ln in lines if ln.customer_id}
    customers = _existing(db, Customer, Customer.external_key, workspace_id, customer_keys)
    for ln in lines:
        if ln.customer_id and ln.customer_id not in customers:
            c = Customer(
                workspace_id=workspace_id,
                external_key=ln.customer_id,
                region=ln.region,
                city=ln.city,
            )
            db.add(c)
            customers[ln.customer_id] = c
            res.customers_created += 1
    db.flush()

    orders: dict[str, Order] = {}
    for ln in lines:
        o = orders.get(ln.order_id)
        if o is None:
            cust = customers.get(ln.customer_id) if ln.customer_id else None
            placed_at, business_date = to_utc_and_business_date(ln.order_date, timezone)
            o = Order(
                workspace_id=workspace_id,
                external_key=ln.order_id,
                customer_id=cust.id if cust else None,
                dataset_id=dataset_id,
                order_date=placed_at,
                business_date=business_date,
                status=ln.status,
                channel=ln.channel,
                currency=currency,
                tax_amount=Decimal("0"),
            )
            db.add(o)
            orders[ln.order_id] = o
            res.orders_created += 1
        o.tax_amount = (o.tax_amount or Decimal("0")) + ln.tax_amount
    db.flush()

    for ln in lines:
        prod = products[ln.sku]
        db.add(
            OrderItem(
                workspace_id=workspace_id,
                order_id=orders[ln.order_id].id,
                product_id=prod.id,
                quantity=ln.quantity,
                unit_price=ln.unit_price,
                discount_amount=ln.discount,
                unit_cost_snapshot=ln.unit_cost if ln.unit_cost is not None else prod.unit_cost,
            )
        )
        res.lines_imported += 1
    db.flush()
    return res
