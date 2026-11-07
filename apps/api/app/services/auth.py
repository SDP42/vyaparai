from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, ConflictError
from app.core.security import hash_password, verify_dummy_password, verify_password
from app.models.user import User
from app.schemas.auth import UserCreate
from app.services import audit


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(User.email == email.strip().lower())).one_or_none()


def register_user(db: Session, data: UserCreate) -> User:
    if get_user_by_email(db, data.email) is not None:
        raise ConflictError("An account with this email already exists")
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("An account with this email already exists") from exc
    audit.record(db, action="user.registered", actor_user_id=user.id, entity_type="user",
                 entity_id=user.id)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None:
        verify_dummy_password(password)
        raise AuthenticationError("Incorrect email or password")
    if not verify_password(password, user.hashed_password) or not user.is_active:
        raise AuthenticationError("Incorrect email or password")
    return user
