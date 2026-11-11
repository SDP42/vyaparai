"""Stock cover and reorder advice.

GET  /workspaces/{id}/inventory/overview       status, cover, order quantities, cash tied up (viewer)
POST /workspaces/{id}/inventory/import         upload a stock CSV (analyst)
PUT  /workspaces/{id}/inventory/items/{sku}    set stock, lead time, pack size (analyst)
GET  /workspaces/{id}/inventory/template.csv   a starter file with your products (viewer)
GET  /workspaces/{id}/inventory/order-list.csv the suggested purchase list (analyst, audited)
"""

import csv
import io
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from app.api.deps import AnalystCtx, DbSession, ViewerCtx
from app.api.masking import MaskedRoute
from app.models.commerce import Product
from app.schemas.inventory import ImportResult, InventoryOverview, ItemUpdate
from app.services import audit, inventory

router = APIRouter(
    prefix="/workspaces/{workspace_id}/inventory", tags=["inventory"], route_class=MaskedRoute
)
Service = Annotated[
    Decimal, Query(ge=0, le=1, description="0 lean, 1 cautious (share of the p50 to p90 gap)")
]
Review = Annotated[int, Query(ge=1, le=60, description="Days between orders")]
MAX_BYTES = 5 * 1024 * 1024


@router.get("/overview", response_model=InventoryOverview)
def overview(
    ctx: ViewerCtx, db: DbSession, service: Service = Decimal("0.5"), review_days: Review = 7
) -> dict[str, Any]:
    return inventory.overview(db, ctx.workspace, service=service, review_days=review_days)


@router.post("/import", response_model=ImportResult)
async def import_stock(
    ctx: AnalystCtx,
    db: DbSession,
    file: Annotated[UploadFile, File()],
    as_of: Annotated[date | None, Form()] = None,
) -> dict[str, Any]:
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise inventory.BadFileError("The file is larger than 5 MB.")
    res = inventory.import_stock(db, ctx.workspace_id, content, as_of or datetime.now(UTC).date())
    audit.record(
        db,
        action="inventory.imported",
        actor_user_id=ctx.user.id,
        workspace_id=ctx.workspace_id,
        entity_type="inventory",
        entity_id=None,
        details={
            "imported": res["imported"],
            "rejected": res["rejected_count"],
            "unmatched": res["unmatched"],
        },
    )
    db.commit()
    return res


@router.put("/items/{sku}", status_code=204)
def update_item(sku: str, data: ItemUpdate, ctx: AnalystCtx, db: DbSession) -> Response:
    inventory.update_item(
        db,
        ctx.workspace_id,
        sku,
        on_hand=data.on_hand,
        as_of=data.as_of,
        lead_time_days=data.lead_time_days,
        pack_size=data.pack_size,
        safety_days=data.safety_days,
    )
    return Response(status_code=204)


@router.get("/template.csv")
def template(ctx: ViewerCtx, db: DbSession) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["SKU", "Product", "Stock", "Date", "Lead time days", "Pack size"])
    for p in db.scalars(
        select(Product)
        .where(Product.workspace_id == ctx.workspace_id, Product.active.is_(True))
        .order_by(Product.sku)
        .limit(500)
    ):
        w.writerow([p.sku, p.name, "", "", "", ""])
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="stock-template.csv"'},
    )


@router.get("/order-list.csv")
def order_list(
    ctx: AnalystCtx, db: DbSession, service: Service = Decimal("0.5"), review_days: Review = 7
) -> Response:
    ov = inventory.overview(db, ctx.workspace, service=service, review_days=review_days)
    audit.record(
        db,
        action="inventory.order_list_exported",
        actor_user_id=ctx.user.id,
        workspace_id=ctx.workspace_id,
        entity_type="inventory",
        entity_id=None,
        details={"lines": sum(1 for i in ov["items"] if i["order_qty"] > 0)},
    )
    db.commit()
    return Response(
        inventory.order_list_csv(ov["items"]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="order-list.csv"'},
    )
