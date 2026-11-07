"""Shared FastAPI dependencies: DB session, current user and workspace authorization."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Path
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError, NotFoundError, PermissionDeniedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceRole
from app.services.workspaces import get_membership

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_settings().api_v1_prefix}/auth/login", auto_error=False
)


def get_current_user(
    db: DbSession, settings: AppSettings, token: Annotated[str | None, Depends(oauth2_scheme)]
) -> User:
    if not token:
        raise AuthenticationError("Not authenticated")
    payload = decode_access_token(token, settings)
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except ValueError as exc:
        raise AuthenticationError("Invalid token subject") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass(frozen=True, slots=True)
class WorkspaceContext:
    workspace: Workspace
    user: User
    role: WorkspaceRole

    @property
    def workspace_id(self) -> uuid.UUID:
        return self.workspace.id


def get_workspace_context(
    workspace_id: Annotated[uuid.UUID, Path()], db: DbSession, user: CurrentUser
) -> WorkspaceContext:
    """Resolve the workspace and the caller's membership.

    Non-members get 404 rather than 403 so workspace IDs cannot be probed.
    """
    membership = get_membership(db, workspace_id, user.id)
    workspace = db.get(Workspace, workspace_id) if membership else None
    if membership is None or workspace is None:
        raise NotFoundError("Workspace not found")
    return WorkspaceContext(workspace=workspace, user=user, role=membership.role)


def require_role(minimum: WorkspaceRole) -> Callable[..., WorkspaceContext]:
    def _dependency(
        ctx: Annotated[WorkspaceContext, Depends(get_workspace_context)],
    ) -> WorkspaceContext:
        if not ctx.role.at_least(minimum):
            raise PermissionDeniedError(f"Requires {minimum.value} role or higher")
        return ctx

    return _dependency


ViewerCtx = Annotated[WorkspaceContext, Depends(require_role(WorkspaceRole.VIEWER))]
AnalystCtx = Annotated[WorkspaceContext, Depends(require_role(WorkspaceRole.ANALYST))]
AdminCtx = Annotated[WorkspaceContext, Depends(require_role(WorkspaceRole.ADMIN))]
