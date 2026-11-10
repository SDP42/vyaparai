"""Pricing and promotion advice: did discounts pay off, and which price moves look safe."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import DbSession, ViewerCtx
from app.services import pricing

router = APIRouter(prefix="/workspaces/{workspace_id}/pricing", tags=["pricing"])


@router.get("/discounts")
def discounts(ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return pricing.discounts(db, ctx.workspace_id)


@router.get("/moves")
def moves(ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return pricing.price_moves(db, ctx.workspace_id)
