"""Canonical import fields and header-matching suggestions."""

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Field:
    key: str
    label: str
    required: bool
    kind: str  # "text" | "number" | "date" | "status"
    synonyms: tuple[str, ...]


FIELDS: tuple[Field, ...] = (
    Field(
        "order_id",
        "Order / invoice ID",
        True,
        "text",
        (
            "order id",
            "order no",
            "order number",
            "invoice",
            "invoice id",
            "invoice no",
            "invoice number",
            "bill no",
            "bill number",
            "voucher no",
            "transaction id",
            "order",
        ),
    ),
    Field(
        "order_date",
        "Order date",
        True,
        "date",
        (
            "order date",
            "date",
            "bill date",
            "invoice date",
            "transaction date",
            "sale date",
            "invoicedate",
            "voucher date",
        ),
    ),
    Field(
        "sku",
        "SKU / item code",
        True,
        "text",
        (
            "sku",
            "item code",
            "product code",
            "stockcode",
            "stock code",
            "code",
            "item id",
            "product id",
            "barcode",
        ),
    ),
    Field(
        "product_name",
        "Product name",
        True,
        "text",
        (
            "product name",
            "item name",
            "item",
            "product",
            "description",
            "particulars",
            "item description",
        ),
    ),
    Field("quantity", "Quantity", True, "number", ("quantity", "qty", "units", "pcs", "nos")),
    Field(
        "unit_price",
        "Unit price",
        True,
        "number",
        ("unit price", "rate", "price", "selling price", "unitprice", "sale price", "mrp"),
    ),
    Field("category", "Category", False, "text", ("category", "department", "group", "item group")),
    Field(
        "discount",
        "Discount (amount per line)",
        False,
        "number",
        ("discount", "disc", "discount amount", "disc amt"),
    ),
    Field(
        "unit_cost",
        "Unit cost",
        False,
        "number",
        ("unit cost", "cost", "cost price", "purchase price", "buying price"),
    ),
    Field(
        "customer_id",
        "Customer ID",
        False,
        "text",
        (
            "customer id",
            "customer",
            "customer code",
            "party",
            "party code",
            "customerid",
            "customer number",
            "phone",
        ),
    ),
    Field("region", "Region / state", False, "text", ("region", "state", "zone")),
    Field("city", "City", False, "text", ("city", "town", "location")),
    Field("channel", "Channel", False, "text", ("channel", "source", "sales channel", "mode")),
    Field("status", "Order status", False, "status", ("status", "order status", "state of order")),
    Field(
        "tax_amount",
        "Tax (GST) amount",
        False,
        "number",
        ("tax", "gst", "tax amount", "gst amount", "igst", "total tax"),
    ),
)

FIELD_BY_KEY = {f.key: f for f in FIELDS}
REQUIRED = tuple(f.key for f in FIELDS if f.required)


def normalise_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", h.lower()).strip()


def suggest_mapping(headers: list[str]) -> dict[str, str]:
    """Map canonical field → source header using exact, then contains, synonym matches."""
    norm = {h: normalise_header(h) for h in headers}
    used: set[str] = set()
    out: dict[str, str] = {}
    for strict in (True, False):
        for field in FIELDS:
            if field.key in out:
                continue
            for syn in field.synonyms:
                match = next(
                    (
                        h
                        for h, n in norm.items()
                        if h not in used and (n == syn if strict else (syn in n and len(syn) > 3))
                    ),
                    None,
                )
                if match:
                    out[field.key] = match
                    used.add(match)
                    break
    return out
