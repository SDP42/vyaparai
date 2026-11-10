"""Link sources: connect a published Google Sheet or shared file and keep the data fresh.

GET    /workspaces/{id}/sources                 the connected links and how their last check went
POST   /workspaces/{id}/sources                 connect a link (analyst)
PATCH  /workspaces/{id}/sources/{source}        rename, change schedule, pause or resume (analyst)
DELETE /workspaces/{id}/sources/{source}        remove a link (analyst); imported data stays
POST   /workspaces/{id}/sources/{source}/run    check the link now (analyst); runs in the background
GET    /workspaces/{id}/sources/{source}/runs   recent checks
"""

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Response, status
from sqlalchemy import select

from app.api.deps import AnalystCtx, DbSession, ViewerCtx
from app.core.errors import NotFoundError
from app.models.source import ImportSource, SourceRun
from app.schemas.source import SourceIn, SourceRead, SourceRunRead, SourceUpdate
from app.services import audit, sources

router = APIRouter(prefix="/workspaces/{workspace_id}/sources", tags=["sources"])


def _get(db: DbSession, ws: uuid.UUID, source_id: uuid.UUID) -> ImportSource:
    s = db.get(ImportSource, source_id)
    if s is None or s.workspace_id != ws:
        raise NotFoundError("Link not found")
    return s


@router.get("", response_model=list[SourceRead])
def list_sources(ctx: ViewerCtx, db: DbSession) -> list[ImportSource]:
    return list(
        db.scalars(
            select(ImportSource)
            .where(ImportSource.workspace_id == ctx.workspace_id)
            .order_by(ImportSource.created_at)
        ).all()
    )


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create(data: SourceIn, ctx: AnalystCtx, db: DbSession) -> ImportSource:
    src = sources.create_source(
        db, ctx.workspace_id, ctx.user.id, data.name, data.url, data.schedule
    )
    audit.record(
        db,
        action="source.created",
        actor_user_id=ctx.user.id,
        workspace_id=ctx.workspace_id,
        entity_type="import_source",
        entity_id=src.id,
        details={"schedule": data.schedule},
    )
    db.commit()
    return src


@router.patch("/{source_id}", response_model=SourceRead)
def update(
    source_id: uuid.UUID, data: SourceUpdate, ctx: AnalystCtx, db: DbSession
) -> ImportSource:
    s = _get(db, ctx.workspace_id, source_id)
    if data.name is not None:
        s.name = data.name.strip()
    if data.schedule is not None:
        s.schedule = data.schedule
    if data.enabled is not None:
        s.enabled = data.enabled
        if data.enabled:
            s.failures = 0  # resuming gives it a fresh start
    db.commit()
    return s


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(source_id: uuid.UUID, ctx: AnalystCtx, db: DbSession) -> Response:
    s = _get(db, ctx.workspace_id, source_id)
    audit.record(
        db,
        action="source.deleted",
        actor_user_id=ctx.user.id,
        workspace_id=ctx.workspace_id,
        entity_type="import_source",
        entity_id=s.id,
    )
    db.delete(s)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{source_id}/run", response_model=SourceRead, status_code=status.HTTP_202_ACCEPTED)
def run_now(
    source_id: uuid.UUID, ctx: AnalystCtx, db: DbSession, background: BackgroundTasks
) -> ImportSource:
    s = _get(db, ctx.workspace_id, source_id)
    if s.last_status != "running":
        s.last_status = "running"
        db.commit()
        background.add_task(sources.run_source, db.get_bind(), s.id)  # type: ignore[arg-type]
    return s


@router.get("/{source_id}/runs", response_model=list[SourceRunRead])
def runs(source_id: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> list[Any]:
    _get(db, ctx.workspace_id, source_id)
    return list(
        db.scalars(
            select(SourceRun)
            .where(SourceRun.source_id == source_id)
            .order_by(SourceRun.created_at.desc())
            .limit(20)
        ).all()
    )
