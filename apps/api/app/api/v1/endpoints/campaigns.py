"""Campaign planning: audience, margin-safe offer, messages, holdout. Nothing is sent.

GET /workspaces/{id}/campaigns/playbook      what to do for each segment, with sizes (viewer)
GET /workspaces/{id}/campaigns/plan          audience, offers, projection and messages (viewer)
GET /workspaces/{id}/campaigns/export.csv    the full contact list for manual sending (analyst, audited)
"""

import csv
import io
from collections.abc import Iterator
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.api.deps import AnalystCtx, DbSession, ViewerCtx
from app.api.masking import MaskedRoute
from app.schemas.campaigns import CampaignPlan, PlaybookEntry
from app.services import audit, campaigns

router = APIRouter(
    prefix="/workspaces/{workspace_id}/campaigns", tags=["campaigns"], route_class=MaskedRoute
)

Segment = Annotated[str, Query(max_length=30)]
AsOf = Annotated[date | None, Query()]
Lookback = Annotated[int, Query(ge=30, le=1095)]
MaxDiscount = Annotated[
    int | None, Query(ge=0, le=30, description="Ceiling for the offer, in percent")
]
Floor = Annotated[
    int, Query(ge=0, le=60, description="Margin that must be kept after the discount")
]
Holdout = Annotated[
    int, Query(ge=0, le=30, description="Share of the audience kept out to measure the effect")
]
Lang = Annotated[campaigns.Language, Query()]
ValidDays = Annotated[int, Query(ge=1, le=30)]


@router.get("/playbook", response_model=list[PlaybookEntry])
def playbook(
    ctx: ViewerCtx, db: DbSession, as_of: AsOf = None, lookback_days: Lookback = 365
) -> list[dict[str, Any]]:
    return campaigns.playbook(db, ctx.workspace, as_of, lookback_days)


@router.get("/plan", response_model=CampaignPlan)
def plan(
    ctx: ViewerCtx,
    db: DbSession,
    segment: Segment,
    as_of: AsOf = None,
    lookback_days: Lookback = 365,
    max_discount: MaxDiscount = None,
    margin_floor: Floor = 15,
    holdout_pct: Holdout = 10,
    language: Lang = "en",
    valid_days: ValidDays = 7,
    limit: Annotated[int, Query(ge=1, le=200)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    p = campaigns.plan(
        db,
        ctx.workspace,
        segment=segment,
        as_of=as_of,
        lookback=lookback_days,
        max_discount=max_discount,
        margin_floor=margin_floor,
        holdout_pct=holdout_pct,
        language=language,
        valid_days=valid_days,
    )
    rows = p.pop("rows")
    return {
        **p,
        "rows": rows[offset : offset + limit],
        "total_rows": len(rows),
        "limit": limit,
        "offset": offset,
    }


@router.get("/export.csv", response_class=StreamingResponse)
def export(
    ctx: AnalystCtx,
    db: DbSession,
    segment: Segment,
    as_of: AsOf = None,
    lookback_days: Lookback = 365,
    max_discount: MaxDiscount = None,
    margin_floor: Floor = 15,
    holdout_pct: Holdout = 10,
    language: Lang = "en",
    valid_days: ValidDays = 7,
) -> StreamingResponse:
    p = campaigns.plan(
        db,
        ctx.workspace,
        segment=segment,
        as_of=as_of,
        lookback=lookback_days,
        max_discount=max_discount,
        margin_floor=margin_floor,
        holdout_pct=holdout_pct,
        language=language,
        valid_days=valid_days,
    )
    audit.record(
        db,
        action="campaign.exported",
        actor_user_id=ctx.user.id,
        workspace_id=ctx.workspace.id,
        entity_type="campaign",
        entity_id=None,
        details={"segment": segment, "rows": len(p["rows"]), "holdout_pct": holdout_pct},
    )
    db.commit()

    def lines() -> Iterator[str]:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(
            [
                "customer",
                "group",
                "segment",
                "city",
                "last_order",
                "days_since_last_order",
                "reason",
                "product",
                "discount_pct",
                "consent_status",
                "message",
            ]
        )
        yield buf.getvalue()
        for r in p["rows"]:
            buf.seek(0)
            buf.truncate()
            w.writerow(
                [
                    r["key"],
                    "holdout" if r["holdout"] else "contact",
                    segment,
                    r["city"] or "",
                    r["last_order"],
                    r["recency_days"],
                    r["reason"],
                    r["product"],
                    r["discount_pct"],
                    r["consent_status"],
                    "" if r["holdout"] else r["message"],
                ]
            )
            yield buf.getvalue()

    return StreamingResponse(
        lines(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="campaign-{segment.lower().replace(" ", "-")}.csv"'
        },
    )
