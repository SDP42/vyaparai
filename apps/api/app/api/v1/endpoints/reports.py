"""Reports: save a business summary for a period, then open it, print it as PDF or export CSV."""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query, Response, status
from pydantic import BaseModel

from app.api.deps import AdminCtx, AnalystCtx, DbSession, ViewerCtx
from app.models.report import SavedReport
from app.services.reports import render, service

router = APIRouter(prefix="/workspaces/{workspace_id}/reports", tags=["reports"])


class ReportIn(BaseModel):
    date_from: date | None = None
    date_to: date | None = None


def _meta(r: SavedReport) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "title": r.title,
        "kind": r.kind,
        "from": r.period_start.isoformat(),
        "to": r.period_end.isoformat(),
        "created_at": r.created_at.isoformat(),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create(data: ReportIn, ctx: AnalystCtx, db: DbSession) -> dict[str, Any]:
    r = service.create(db, ctx.workspace, ctx.user.id, data.date_from, data.date_to)
    return {**_meta(r), "content": r.content}


@router.get("")
def listing(
    ctx: ViewerCtx, db: DbSession, limit: Annotated[int, Query(ge=1, le=100)] = 30
) -> list[dict[str, Any]]:
    return [_meta(r) for r in service.listing(db, ctx.workspace_id, limit)]


@router.get("/{report_id}")
def get_report(report_id: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    r = service.get(db, ctx.workspace_id, report_id)
    return {**_meta(r), "content": r.content}


@router.get("/{report_id}/pdf")
def pdf(report_id: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> Response:
    r = service.get(db, ctx.workspace_id, report_id)
    return Response(
        render.to_pdf(r.content),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="business-summary-{r.period_start}-{r.period_end}.pdf"'
        },
    )


@router.get("/{report_id}/csv")
def csv_export(report_id: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> Response:
    r = service.get(db, ctx.workspace_id, report_id)
    return Response(
        render.to_csv(r.content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="business-summary-{r.period_start}-{r.period_end}.csv"'
        },
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(report_id: uuid.UUID, ctx: AdminCtx, db: DbSession) -> Response:
    service.remove(db, service.get(db, ctx.workspace_id, report_id), ctx.user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
