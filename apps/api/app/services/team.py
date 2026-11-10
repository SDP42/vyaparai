"""Team management: change roles, remove members, one-time invitation links.

Rules: a workspace always keeps at least one owner; only an owner can grant, change or remove an
owner; an admin can manage analysts and viewers; nobody manages a role above their own.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.models.session import Invitation
from app.models.user import User
from app.models.workspace import Membership, Workspace, WorkspaceRole
from app.schemas.workspace import InvitationRead, MemberRead
from app.services import audit
from app.services.workspaces import get_membership

INVITE_DAYS = 7


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _owner_count(db: Session, workspace_id: uuid.UUID) -> int:
    rows = db.scalars(
        select(Membership).where(
            Membership.workspace_id == workspace_id, Membership.role == WorkspaceRole.OWNER
        )
    ).all()
    return len(rows)


def _check_may_manage(actor_role: WorkspaceRole, target_role: WorkspaceRole) -> None:
    if target_role == WorkspaceRole.OWNER and actor_role != WorkspaceRole.OWNER:
        raise PermissionDeniedError("Only an owner can change or remove an owner")


def change_role(
    db: Session,
    workspace: Workspace,
    actor: User,
    actor_role: WorkspaceRole,
    user_id: uuid.UUID,
    role: WorkspaceRole,
) -> MemberRead:
    m = get_membership(db, workspace.id, user_id)
    if m is None:
        raise NotFoundError("That person is not a member of this workspace")
    _check_may_manage(actor_role, m.role)
    _check_may_manage(actor_role, role)
    last_owner = m.role == WorkspaceRole.OWNER and _owner_count(db, workspace.id) <= 1
    if last_owner and role != WorkspaceRole.OWNER:
        raise ConflictError("A workspace needs at least one owner")
    before = m.role
    m.role = role
    audit.record(
        db, action="workspace.member_role_changed", actor_user_id=actor.id,
        workspace_id=workspace.id, entity_type="user", entity_id=user_id,
        details={"from": before.value, "to": role.value},
    )  # fmt: skip
    db.commit()
    u = db.get(User, user_id)
    if u is None:
        raise NotFoundError("User not found")
    return MemberRead(
        user_id=u.id, email=u.email, full_name=u.full_name, role=m.role, joined_at=m.created_at
    )


def remove_member(
    db: Session,
    workspace: Workspace,
    actor: User,
    actor_role: WorkspaceRole,
    user_id: uuid.UUID,
) -> None:
    m = get_membership(db, workspace.id, user_id)
    if m is None:
        raise NotFoundError("That person is not a member of this workspace")
    _check_may_manage(actor_role, m.role)
    if m.role == WorkspaceRole.OWNER and _owner_count(db, workspace.id) <= 1:
        raise ConflictError("A workspace needs at least one owner")
    db.delete(m)
    audit.record(
        db, action="workspace.member_removed", actor_user_id=actor.id,
        workspace_id=workspace.id, entity_type="user", entity_id=user_id,
        details={"role": m.role.value},
    )  # fmt: skip
    db.commit()


def _status(inv: Invitation) -> str:
    if inv.revoked_at is not None:
        return "revoked"
    if inv.used_at is not None:
        return "used"
    return "expired" if _aware(inv.expires_at) <= _now() else "pending"


def _read(inv: Invitation) -> InvitationRead:
    return InvitationRead(
        id=inv.id, role=WorkspaceRole(inv.role), expires_at=inv.expires_at, status=_status(inv)
    )


def create_invitation(
    db: Session,
    workspace: Workspace,
    actor: User,
    actor_role: WorkspaceRole,
    role: WorkspaceRole,
) -> tuple[InvitationRead, str]:
    _check_may_manage(actor_role, role)
    token = secrets.token_urlsafe(32)
    inv = Invitation(
        workspace_id=workspace.id, role=role.value, token_hash=_hash(token),
        expires_at=_now() + timedelta(days=INVITE_DAYS), created_by_id=actor.id,
    )  # fmt: skip
    db.add(inv)
    db.flush()
    audit.record(
        db, action="workspace.invitation_created", actor_user_id=actor.id,
        workspace_id=workspace.id, entity_type="invitation", entity_id=inv.id,
        details={"role": role.value},
    )  # fmt: skip
    db.commit()
    return _read(inv), token


def list_invitations(db: Session, workspace_id: uuid.UUID) -> list[InvitationRead]:
    rows = db.scalars(
        select(Invitation)
        .where(Invitation.workspace_id == workspace_id)
        .order_by(Invitation.created_at.desc())
        .limit(50)
    ).all()
    return [_read(i) for i in rows]


def revoke_invitation(
    db: Session, workspace: Workspace, actor: User, invitation_id: uuid.UUID
) -> None:
    inv = db.get(Invitation, invitation_id)
    if inv is None or inv.workspace_id != workspace.id:
        raise NotFoundError("Invitation not found")
    if inv.revoked_at is None and inv.used_at is None:
        inv.revoked_at = _now()
        audit.record(
            db, action="workspace.invitation_revoked", actor_user_id=actor.id,
            workspace_id=workspace.id, entity_type="invitation", entity_id=inv.id,
        )  # fmt: skip
        db.commit()


def accept_invitation(db: Session, user: User, token: str) -> Workspace:
    inv = db.scalars(select(Invitation).where(Invitation.token_hash == _hash(token))).first()
    if inv is None or _status(inv) != "pending":
        raise NotFoundError("This invitation is not valid any more")  # same answer for all cases
    ws = db.get(Workspace, inv.workspace_id)
    if ws is None:
        raise NotFoundError("This invitation is not valid any more")
    if get_membership(db, ws.id, user.id) is not None:
        raise ConflictError("You are already a member of this workspace")
    db.add(Membership(workspace_id=ws.id, user_id=user.id, role=WorkspaceRole(inv.role)))
    inv.used_at = _now()
    audit.record(
        db, action="workspace.invitation_accepted", actor_user_id=user.id,
        workspace_id=ws.id, entity_type="invitation", entity_id=inv.id,
        details={"role": inv.role},
    )  # fmt: skip
    db.commit()
    return ws
