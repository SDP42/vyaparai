"""Purchase bills: upload a photo or PDF, check what was read, confirm, and watch supplier prices."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, File, Query, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AnalystCtx, DbSession, ViewerCtx
from app.models.bill import PurchaseBill
from app.models.commerce import Product
from app.services.bills import reader, service

router = APIRouter(prefix="/workspaces/{workspace_id}/bills", tags=["bills"])


class LineIn(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    quantity: Decimal = Field(gt=0, max_digits=14)
    unit_price: Decimal = Field(ge=0, max_digits=14)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=16)
    unit: str | None = Field(default=None, max_length=12)
    product_id: uuid.UUID | None = None


class BillUpdate(BaseModel):
    supplier: str | None = Field(default=None, max_length=160)
    gstin: str | None = Field(default=None, max_length=15)
    bill_no: str | None = Field(default=None, max_length=40)
    bill_date: date | None = None
    total: Decimal | None = Field(default=None, ge=0, max_digits=16)
    lines: list[LineIn] | None = Field(default=None, max_length=300)


def _bill(b: PurchaseBill, detail: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": str(b.id), "status": b.status, "supplier": b.supplier, "gstin": b.gstin,
        "bill_no": b.bill_no, "bill_date": b.bill_date.isoformat() if b.bill_date else None,
        "total": None if b.total is None else str(b.total), "engine": b.engine,
        "warnings": [w for w in b.warnings.split("\n") if w], "line_count": len(b.lines),
        "created_at": b.created_at.isoformat(),
    }  # fmt: skip
    if detail:
        out["lines"] = [
            {
                "description": x.description, "quantity": str(x.quantity),
                "unit_price": str(x.unit_price), "amount": str(x.amount), "unit": x.unit,
                "confidence": x.confidence, "product_id": str(x.product_id) if x.product_id else None,
            }
            for x in b.lines
        ]  # fmt: skip
    return out


@router.get("/engines")
def engines(ctx: ViewerCtx) -> dict[str, Any]:
    return {"engines": reader.available_engines(), "max_mb": reader.MAX_BYTES // (1024 * 1024)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload(
    ctx: AnalystCtx, db: DbSession, file: Annotated[UploadFile, File()]
) -> dict[str, Any]:
    content = await file.read(reader.MAX_BYTES + 1)
    return _bill(service.create_from_file(db, ctx.workspace_id, ctx.user.id, content))


@router.get("")
def list_bills(
    ctx: ViewerCtx,
    db: DbSession,
    state: Annotated[str | None, Query(pattern="^(draft|confirmed)$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[dict[str, Any]]:
    stmt = select(PurchaseBill).where(PurchaseBill.workspace_id == ctx.workspace_id)
    if state:
        stmt = stmt.where(PurchaseBill.status == state)
    rows = db.scalars(stmt.order_by(PurchaseBill.created_at.desc()).limit(limit))
    return [_bill(b, detail=False) for b in rows]


@router.get("/products")
def product_choices(ctx: ViewerCtx, db: DbSession) -> list[dict[str, str]]:
    """Products a bill line can be matched to (for the review screen's picker)."""
    rows = db.scalars(
        select(Product)
        .where(Product.workspace_id == ctx.workspace_id, Product.active.is_(True))
        .order_by(Product.name)
        .limit(1000)
    )
    return [{"id": str(p.id), "sku": p.sku, "name": p.name} for p in rows]


@router.get("/prices/moves")
def price_moves(ctx: ViewerCtx, db: DbSession) -> list[dict[str, Any]]:
    return service.price_moves(db, ctx.workspace_id)


@router.get("/prices/{product_id}")
def price_history(product_id: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> list[dict[str, Any]]:
    return service.history(db, ctx.workspace_id, product_id)


@router.get("/{bill_id}")
def get_bill(bill_id: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return _bill(service.get(db, ctx.workspace_id, bill_id))


@router.put("/{bill_id}")
def update_bill(
    bill_id: uuid.UUID, data: BillUpdate, ctx: AnalystCtx, db: DbSession
) -> dict[str, Any]:
    bill = service.get(db, ctx.workspace_id, bill_id)
    payload = data.model_dump(exclude_unset=True)
    return _bill(service.update(db, bill, payload))


@router.post("/{bill_id}/confirm")
def confirm_bill(bill_id: uuid.UUID, ctx: AnalystCtx, db: DbSession) -> dict[str, Any]:
    return service.confirm(db, service.get(db, ctx.workspace_id, bill_id), ctx.user.id)


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def discard_bill(bill_id: uuid.UUID, ctx: AnalystCtx, db: DbSession) -> Response:
    service.delete_draft(db, service.get(db, ctx.workspace_id, bill_id), ctx.user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
