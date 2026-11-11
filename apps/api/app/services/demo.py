"""Demo accounts, one per persona, so each job in the shop can be tried with one tap.

Only available when DEMO_LOGIN_ENABLED=true, which the settings refuse in production.
The accounts have random passwords nobody knows: they can only be entered through the
demo sign-in, never by typing a password.
"""

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.models.workspace import Membership, Workspace, WorkspaceRole
from app.schemas.workspace import WorkspaceCreate
from app.services import personas
from app.services.auth import get_user_by_email
from app.services.workspaces import create_workspace

DOMAIN = "example.com"
NAMES = {
    "owner": "Meera Kulkarni",
    "ops_manager": "Arjun Mehta",
    "analyst": "Zoya Siddiqui",
    "accountant": "Kabir Rao",
    "cashier": "Sunita Patil",
}
SHOP = "Kulkarni General Store"


def email_for(persona: str) -> str:
    return (
        f"demo.{persona.replace('_', '-')}@{DOMAIN}"
        if persona != "owner"
        else f"demo.owner@{DOMAIN}"
    )


def _user(db: Session, persona: str) -> User:
    email = email_for(persona)
    user = get_user_by_email(db, email)
    if user is None:
        user = User(
            email=email,
            full_name=NAMES[persona],
            hashed_password=hash_password(secrets.token_urlsafe(24)),
        )
        db.add(user)
        db.flush()
    return user


def _shop(db: Session, owner: User) -> Workspace:
    ws = db.scalars(
        select(Workspace)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == owner.id, Membership.role == WorkspaceRole.OWNER)
        .order_by(Workspace.created_at)
    ).first()
    return ws if ws is not None else create_workspace(db, owner, WorkspaceCreate(name=SHOP))


def ensure_persona_user(db: Session, persona: str) -> User:
    """Create the persona's demo user if missing and attach it to the demo shop."""
    if persona not in personas.PERSONAS:
        raise KeyError(persona)
    owner = _user(db, "owner")
    ws = _shop(db, owner)
    user = owner if persona == "owner" else _user(db, persona)
    wanted = personas.PERSONAS[persona]
    m = db.scalars(
        select(Membership).where(Membership.workspace_id == ws.id, Membership.user_id == user.id)
    ).one_or_none()
    if m is None:
        db.add(
            Membership(
                workspace_id=ws.id, user_id=user.id, role=wanted.default_role, persona=persona
            )
        )
    else:
        m.persona = persona
        if persona != "owner":
            m.role = wanted.default_role
    db.commit()
    return user
