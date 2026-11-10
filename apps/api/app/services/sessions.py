"""Sign-in sessions: a short-lived access token plus a rotating refresh token in an HttpOnly cookie.

Rules (OWASP Session Management and JWT cheat sheets):
- the refresh token is random, 256 bits, stored only as a SHA-256 hash, and sent as an HttpOnly,
  SameSite=Lax cookie limited to the auth path (Secure in production);
- every refresh issues a new token and marks the old one used (rotation);
- presenting a token that was already used (outside a short grace for two tabs refreshing at once)
  is treated as theft: the whole sign-in family is revoked;
- idle timeout (``refresh_token_days``) and absolute timeout (``session_max_days``);
- logout revokes every token of the family, and "sign out everywhere" revokes all of a user's.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.models.session import RefreshToken
from app.models.user import User

GRACE_SECONDS = 10  # two tabs may refresh with the same cookie at the same moment


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def issue(
    db: Session,
    user: User,
    settings: Settings,
    *,
    family_id: uuid.UUID | None = None,
    family_started_at: datetime | None = None,
    user_agent: str | None = None,
) -> str:
    """Create a refresh token (new family unless one is given) and return it. Caller commits."""
    token = secrets.token_urlsafe(32)
    now = _now()
    started = family_started_at or now
    expires = min(
        now + timedelta(days=settings.refresh_token_days),
        started + timedelta(days=settings.session_max_days),
    )
    db.add(
        RefreshToken(
            user_id=user.id,
            family_id=family_id or uuid.uuid4(),
            token_hash=_hash(token),
            family_started_at=started,
            expires_at=expires,
            user_agent=(user_agent or "")[:200] or None,
        )
    )
    return token


def revoke_family(db: Session, family_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


def revoke_all(db: Session, user_id: uuid.UUID) -> int:
    res = db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    return int(res.rowcount or 0)  # type: ignore[attr-defined]


def rotate(
    db: Session, token: str, settings: Settings, *, user_agent: str | None = None
) -> tuple[User, str]:
    """Exchange a refresh token for a new one. Raises AuthenticationError if it cannot be used."""
    row = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == _hash(token))).first()
    fail = AuthenticationError("Your session has ended. Please sign in again.")
    if row is None:
        raise fail
    now = _now()
    if row.revoked_at is not None:
        raise fail
    if _aware(row.expires_at) <= now:
        revoke_family(db, row.family_id)
        db.commit()
        raise fail
    if row.used_at is not None:
        if now - _aware(row.used_at) > timedelta(seconds=GRACE_SECONDS):
            revoke_family(db, row.family_id)  # an old token came back: assume it was stolen
            db.commit()
            raise fail
    else:
        row.used_at = now
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        revoke_family(db, row.family_id)
        db.commit()
        raise fail
    new = issue(
        db, user, settings, family_id=row.family_id,
        family_started_at=_aware(row.family_started_at), user_agent=user_agent,
    )  # fmt: skip
    db.commit()
    return user, new


def revoke_by_token(db: Session, token: str | None) -> None:
    """Sign out: revoke the whole family of this token (idempotent; unknown tokens are ignored)."""
    if not token:
        return
    row = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == _hash(token))).first()
    if row is not None:
        revoke_family(db, row.family_id)
        db.commit()
