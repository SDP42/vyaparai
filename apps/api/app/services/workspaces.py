import re
import secrets
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.models.user import User
from app.models.workspace import Membership, Workspace, WorkspaceRole
from app.schemas.workspace import MemberAdd, MemberRead, WorkspaceCreate, WorkspaceUpdate
from app.services import audit, personas
from app.services.auth import get_user_by_email


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:120] or "workspace"
    return f"{base}-{secrets.token_hex(3)}"


def create_workspace(db: Session, owner: User, data: WorkspaceCreate) -> Workspace:
    workspace = Workspace(
        name=data.name,
        slug=_slugify(data.name),
        currency=data.currency,
        timezone=data.timezone,
        created_by_id=owner.id,
    )
    db.add(workspace)
    db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=owner.id, role=WorkspaceRole.OWNER))
    audit.record(
        db,
        action="workspace.created",
        actor_user_id=owner.id,
        workspace_id=workspace.id,
        entity_type="workspace",
        entity_id=workspace.id,
    )
    db.commit()
    return workspace


def list_for_user(db: Session, user: User) -> Sequence[tuple[Workspace, WorkspaceRole]]:
    stmt = (
        select(Workspace, Membership.role)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == user.id)
        .order_by(Workspace.created_at)
    )
    return [(ws, role) for ws, role in db.execute(stmt).all()]


def get_membership(db: Session, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Membership | None:
    stmt = select(Membership).where(
        Membership.workspace_id == workspace_id, Membership.user_id == user_id
    )
    return db.scalars(stmt).one_or_none()


def update_workspace(
    db: Session, workspace: Workspace, actor: User, data: WorkspaceUpdate
) -> Workspace:
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(workspace, field, value)
    audit.record(
        db,
        action="workspace.updated",
        actor_user_id=actor.id,
        workspace_id=workspace.id,
        entity_type="workspace",
        entity_id=workspace.id,
        details={"fields": sorted(changes)},
    )
    db.commit()
    return workspace


def list_members(db: Session, workspace_id: uuid.UUID) -> list[MemberRead]:
    stmt = (
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.workspace_id == workspace_id)
        .order_by(Membership.created_at)
    )
    return [
        MemberRead(
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=m.role,
            persona=m.persona,
            staff_name=m.staff_name,
            joined_at=m.created_at,
        )
        for m, u in db.execute(stmt).all()
    ]


def check_persona(persona: str | None, role: WorkspaceRole) -> None:
    if persona is not None and not personas.valid_for_role(persona, role):
        raise AppError(f"The persona '{persona}' does not fit the {role.value} role")


def add_member(
    db: Session, workspace: Workspace, actor: User, actor_role: WorkspaceRole, data: MemberAdd
) -> MemberRead:
    if data.role == WorkspaceRole.OWNER and actor_role != WorkspaceRole.OWNER:
        raise PermissionDeniedError("Only an owner can grant the owner role")
    user = get_user_by_email(db, data.email)
    if user is None:
        raise NotFoundError("No registered user with that email")
    if get_membership(db, workspace.id, user.id) is not None:
        raise ConflictError("User is already a member of this workspace")
    check_persona(data.persona, data.role)
    membership = Membership(
        workspace_id=workspace.id, user_id=user.id, role=data.role, persona=data.persona
    )
    db.add(membership)
    audit.record(
        db,
        action="workspace.member_added",
        actor_user_id=actor.id,
        workspace_id=workspace.id,
        entity_type="user",
        entity_id=user.id,
        details={"role": data.role.value},
    )
    db.commit()
    return MemberRead(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        persona=membership.persona,
        staff_name=membership.staff_name,
        joined_at=membership.created_at,
    )
