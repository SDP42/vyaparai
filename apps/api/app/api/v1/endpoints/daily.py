"""Daily shop routines: Today, day-end cash count, expenses, expiry watch, supplier order lists, quick entries."""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field

from app.api.deps import AdminCtx, DbSession, ViewerCtx, WorkspaceContext, require_capability
from app.api.masking import MaskedRoute
from app.services import daily
from app.services.personas import CAPABILITIES

router = APIRouter(
    prefix="/workspaces/{workspace_id}/daily", tags=["daily"], route_class=MaskedRoute
)
Cash = [Depends(require_capability("cash"))]
Stock = [Depends(require_capability("stock"))]
Supplier = [Depends(require_capability("supplier"))]


def _today() -> date:
    return datetime.now(UTC).date()


def _can(ctx: WorkspaceContext) -> set[str]:
    return set(CAPABILITIES) if ctx.persona is None else set(ctx.persona.capabilities)


@router.get("/today")
def today(ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return daily.today(db, ctx.workspace, _today(), can=_can(ctx))


# ---- day close


class CloseIn(BaseModel):
    day: date
    opening_cash: Decimal = Field(default=Decimal("0"), ge=0)
    cash_sales: Decimal = Field(default=Decimal("0"), ge=0)
    upi_sales: Decimal = Field(default=Decimal("0"), ge=0)
    card_sales: Decimal = Field(default=Decimal("0"), ge=0)
    taken_out: Decimal = Field(default=Decimal("0"), ge=0)
    counted_cash: Decimal = Field(ge=0)
    note: str | None = Field(default=None, max_length=200)


@router.get("/close", dependencies=Cash)
def close_view(ctx: ViewerCtx, db: DbSession, day: date | None = None) -> dict[str, Any]:
    return daily.close_view(db, ctx.workspace, day or _today())


@router.put("/close", dependencies=Cash)
def save_close(data: CloseIn, ctx: AdminCtx, db: DbSession) -> dict[str, Any]:
    return daily.save_close(db, ctx.workspace, ctx.user.id, **data.model_dump())


@router.get("/close/history", dependencies=Cash)
def close_history(
    ctx: ViewerCtx, db: DbSession, days: Annotated[int, Query(ge=1, le=90)] = 30
) -> list[dict[str, Any]]:
    return daily.close_history(db, ctx.workspace, days)


# ---- expenses


class ExpenseIn(BaseModel):
    spent_on: date | None = None
    category: str = Field(max_length=20)
    amount: Decimal = Field(gt=0)
    paid_by: str = Field(default="cash", max_length=10)
    note: str | None = Field(default=None, max_length=200)


@router.get("/expenses", dependencies=Cash)
def list_expenses(
    ctx: ViewerCtx,
    db: DbSession,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> dict[str, Any]:
    end = date_to or _today()
    return daily.expenses(db, ctx.workspace_id, date_from or end.replace(day=1), end)


@router.post("/expenses", dependencies=Cash, status_code=status.HTTP_201_CREATED)
def add_expense(data: ExpenseIn, ctx: AdminCtx, db: DbSession) -> dict[str, Any]:
    e = daily.add_expense(
        db,
        ctx.workspace_id,
        ctx.user.id,
        spent_on=data.spent_on or _today(),
        category=data.category,
        amount=data.amount,
        paid_by=data.paid_by,
        note=data.note,
    )
    return {
        "id": str(e.id),
        "amount": e.amount,
        "category": e.category,
        "spent_on": e.spent_on.isoformat(),
    }


@router.delete("/expenses/{expense_id}", dependencies=Cash, status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: uuid.UUID, ctx: AdminCtx, db: DbSession) -> Response:
    daily.delete_expense(db, ctx.workspace_id, expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/expense-categories")
def categories(_: ViewerCtx) -> list[dict[str, str]]:
    return [
        {"key": k, "en": v[0], "hinglish": v[1], "hi": v[2]} for k, v in daily.CATEGORIES.items()
    ]


# ---- expiry watch


class ExpiryIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    expires_on: date
    quantity: Decimal | None = Field(default=None, ge=0)
    batch: str | None = Field(default=None, max_length=40)
    note: str | None = Field(default=None, max_length=200)


class ClearIn(BaseModel):
    how: str = Field(max_length=20)


@router.get("/expiry", dependencies=Stock)
def expiry(ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return daily.expiry_list(db, ctx.workspace_id, _today())


@router.post("/expiry", dependencies=Stock, status_code=status.HTTP_201_CREATED)
def add_expiry(data: ExpiryIn, ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    if data.expires_on < _today() - timedelta(days=365):
        from app.core.errors import AppError

        raise AppError("That date is more than a year ago")
    item = daily.add_expiry(db, ctx.workspace_id, **data.model_dump())
    return {"id": str(item.id), "name": item.name, "expires_on": item.expires_on.isoformat()}


@router.post("/expiry/{item_id}/clear", dependencies=Stock, status_code=status.HTTP_204_NO_CONTENT)
def clear_expiry(item_id: uuid.UUID, data: ClearIn, ctx: ViewerCtx, db: DbSession) -> Response:
    daily.clear_expiry(db, ctx.workspace_id, item_id, data.how)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- supplier order lists


@router.get("/orders", dependencies=Supplier)
def orders(
    ctx: ViewerCtx,
    db: DbSession,
    lang: Annotated[str, Query(pattern="^(en|hinglish|hi)$")] = "hinglish",
) -> dict[str, Any]:
    return daily.order_lists(db, ctx.workspace, lang)


# ---- one-sentence entries


class QuickIn(BaseModel):
    text: str = Field(min_length=1, max_length=200)


class QuickSave(BaseModel):
    kind: str = Field(pattern="^(credit|payment|expense)$")
    amount: Decimal = Field(gt=0)
    party: str | None = Field(default=None, max_length=120)
    category: str | None = Field(default=None, max_length=20)
    note: str | None = Field(default=None, max_length=200)
    day: date | None = None


@router.post("/quick/parse")
def quick_parse(data: QuickIn, ctx: ViewerCtx) -> dict[str, Any]:
    return daily.parse_entry(data.text)


@router.post("/quick/save", status_code=status.HTTP_201_CREATED)
def quick_save(data: QuickSave, ctx: AdminCtx, db: DbSession) -> dict[str, Any]:
    p = ctx.persona
    need = "cash" if data.kind == "expense" else "credit"
    if p is not None and not p.can(need):
        from app.core.errors import PermissionDeniedError

        raise PermissionDeniedError(f"Not part of the {p.label['en'].lower()} view.")
    return daily.save_entry(
        db, ctx.workspace_id, ctx.user.id, data.model_dump(), data.day or _today()
    )
