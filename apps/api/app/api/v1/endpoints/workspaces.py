import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import AdminCtx, CurrentUser, DbSession, ViewerCtx
from app.models.workspace import Workspace
from app.repositories.datasets import AuditLogRepository
from app.schemas.common import Page
from app.schemas.dataset import AuditLogRead
from app.schemas.workspace import (
    InvitationAccept,
    InvitationCreate,
    InvitationCreated,
    InvitationRead,
    MemberAdd,
    MemberRead,
    MemberRoleUpdate,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
    WorkspaceWithRole,
)
from app.services import team
from app.services import workspaces as workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
join_router = APIRouter(prefix="/invitations", tags=["workspaces"])


@join_router.post("/accept", response_model=WorkspaceRead)
def accept_invitation(data: InvitationAccept, db: DbSession, user: CurrentUser) -> Workspace:
    return team.accept_invitation(db, user, data.token)


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(data: WorkspaceCreate, db: DbSession, user: CurrentUser) -> Workspace:
    return workspace_service.create_workspace(db, user, data)


@router.get("", response_model=list[WorkspaceWithRole])
def list_workspaces(db: DbSession, user: CurrentUser) -> list[WorkspaceWithRole]:
    return [
        WorkspaceWithRole.model_validate(
            {**WorkspaceRead.model_validate(ws).model_dump(), "role": role}
        )
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


@router.patch("/{workspace_id}/members/{user_id}", response_model=MemberRead)
def change_member_role(
    user_id: uuid.UUID, data: MemberRoleUpdate, ctx: AdminCtx, db: DbSession
) -> MemberRead:
    return team.change_role(db, ctx.workspace, ctx.user, ctx.role, user_id, data.role)


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(user_id: uuid.UUID, ctx: AdminCtx, db: DbSession) -> Response:
    team.remove_member(db, ctx.workspace, ctx.user, ctx.role, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{workspace_id}/invitations", response_model=list[InvitationRead])
def list_invitations(ctx: AdminCtx, db: DbSession) -> list[InvitationRead]:
    return team.list_invitations(db, ctx.workspace_id)


@router.post(
    "/{workspace_id}/invitations",
    response_model=InvitationCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_invitation(data: InvitationCreate, ctx: AdminCtx, db: DbSession) -> InvitationCreated:
    inv, token = team.create_invitation(db, ctx.workspace, ctx.user, ctx.role, data.role)
    return InvitationCreated(**inv.model_dump(), token=token)


@router.delete(
    "/{workspace_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT
)
def revoke_invitation(invitation_id: uuid.UUID, ctx: AdminCtx, db: DbSession) -> Response:
    team.revoke_invitation(db, ctx.workspace, ctx.user, invitation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
