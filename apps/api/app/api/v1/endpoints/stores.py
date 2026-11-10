"""Stores: compare the workspaces you belong to, and add another."""

from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.services import stores

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/overview")
def overview(
    user: CurrentUser,
    db: DbSession,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> dict[str, Any]:
    return stores.overview(db, user, date_from, date_to, datetime.now(UTC).date())
