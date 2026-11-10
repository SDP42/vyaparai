"""Customer reviews: import, summary, per-product view, search, and a try-it box."""

import csv
import io
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, File, Query, Response, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import AnalystCtx, DbSession, ViewerCtx
from app.core.errors import AppError
from app.services import audit
from app.services.reviews import analyzer, service

router = APIRouter(prefix="/workspaces/{workspace_id}/reviews", tags=["reviews"])
MAX_BYTES = 5 * 1024 * 1024


class ReviewRead(BaseModel):
    id: uuid.UUID
    review_date: str | None
    rating: int | None
    text: str
    language: str
    sentiment: float
    label: str
    product: str | None
    source: str
    themes: list[dict[str, Any]]


class TryIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.post("/import")
async def import_reviews(
    ctx: AnalystCtx, db: DbSession, file: Annotated[UploadFile, File()]
) -> dict[str, Any]:
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise AppError("The file is larger than 5 MB.")
    res = service.import_reviews(db, ctx.workspace_id, content)
    audit.record(
        db, action="reviews.imported", actor_user_id=ctx.user.id, workspace_id=ctx.workspace_id,
        entity_type="reviews", entity_id=None, details={"added": res["added"]},
    )  # fmt: skip
    db.commit()
    return res


@router.get("/summary")
def summary(
    ctx: ViewerCtx, db: DbSession, days: Annotated[int, Query(ge=7, le=365)] = 90
) -> dict[str, Any]:
    return service.summary(db, ctx.workspace_id, days)


@router.get("/products")
def products(ctx: ViewerCtx, db: DbSession) -> list[dict[str, Any]]:
    return service.by_product(db, ctx.workspace_id)


@router.get("")
def list_reviews(
    ctx: ViewerCtx,
    db: DbSession,
    label: Annotated[str | None, Query(pattern="^(positive|neutral|negative)$")] = None,
    theme: Annotated[str | None, Query(max_length=30)] = None,
    language: Annotated[str | None, Query(pattern="^(en|hi|hinglish)$")] = None,
    product_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    rows, total = service.list_reviews(
        db, ctx.workspace_id, label=label, theme=theme, language=language,
        product_id=product_id, q=q, limit=limit, offset=offset,
    )  # fmt: skip
    items = [
        ReviewRead(
            id=r.id, review_date=r.review_date.isoformat() if r.review_date else None,
            rating=r.rating, text=r.text, language=r.language, sentiment=r.sentiment,
            label=r.label, product=r.product_hint, source=r.source, themes=r.themes or [],
        )
        for r in rows
    ]  # fmt: skip
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/try")
def try_text(data: TryIn, ctx: ViewerCtx) -> dict[str, Any]:
    """Score a sentence without saving it, so the owner can see how a review is read."""
    a = analyzer.analyse(data.text)
    return {
        "language": a.language, "sentiment": a.sentiment, "label": a.label,
        "themes": [t.as_dict() for t in a.themes], "method": analyzer.VERSION,
    }  # fmt: skip


@router.post("/reanalyse")
def reanalyse(ctx: AnalystCtx, db: DbSession) -> dict[str, Any]:
    return service.reanalyse(db, ctx.workspace_id)


@router.get("/template.csv")
def template(ctx: ViewerCtx) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Product", "Rating", "Review", "Source"])
    w.writerow(
        [
            "2026-11-01",
            "Basmati Rice 5kg",
            "5",
            "Bahut accha chawal, delivery time pe aayi",
            "Google",
        ]
    )
    return Response(
        buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="reviews-template.csv"'},
    )  # fmt: skip
