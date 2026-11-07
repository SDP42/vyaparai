from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import AdminCtx, CurrentUser, DbSession, ViewerCtx
from app.models.workspace import Workspace
from app.repositories.datasets import AuditLogRepository
from app.schemas.common import Page
from app.schemas.dataset import AuditLogRead
from app.schemas.workspace import (
    MemberAdd,
    MemberRead,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
    WorkspaceWithRole,
)
from app.services import workspaces as workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(data: WorkspaceCreate, db: DbSession, user: CurrentUser) -> Workspace:
    return workspace_service.create_workspace(db, user, data)


@router.get("", response_model=list[WorkspaceWithRole])
def list_workspaces(db: DbSession, user: CurrentUser) -> list[WorkspaceWithRole]:
    return [
        WorkspaceWithRole.model_validate({**WorkspaceRead.model_validate(ws).model_dump(),
                                          "role": role})
        for ws, role in workspace_service.list_for_user(db, user)
    ]


@router.get("/{workspace_id}", response_model=WorkspaceWithRole)
def get_workspace(ctx: ViewerCtx) -> WorkspaceWithRole:
    return WorkspaceWithRole.model_validate(
        {**WorkspaceRead.model_validate(ctx.workspace).model_dump(), "role": ctx.role}
    )


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(data: WorkspaceUpdate, ctx: AdminCtx, db: DbSession) -> Workspace:
    return workspace_service.update_workspace(db, ctx.workspace, ctx.user, data)


@router.get("/{workspace_id}/members", response_model=list[MemberRead])
def list_members(ctx: ViewerCtx, db: DbSession) -> list[MemberRead]:
    return workspace_service.list_members(db, ctx.workspace_id)


@router.post(
    "/{workspace_id}/members", response_model=MemberRead, status_code=status.HTTP_201_CREATED
)
def add_member(data: MemberAdd, ctx: AdminCtx, db: DbSession) -> MemberRead:
    return workspace_service.add_member(db, ctx.workspace, ctx.user, ctx.role, data)


@router.get("/{workspace_id}/audit-logs", response_model=Page[AuditLogRead])
def list_audit_logs(
    ctx: AdminCtx,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[AuditLogRead]:
    repo = AuditLogRepository(db, ctx.workspace_id)
    items = [AuditLogRead.model_validate(x) for x in repo.list(limit=limit, offset=offset)]
    return Page(items=items, total=repo.count(), limit=limit, offset=offset)
