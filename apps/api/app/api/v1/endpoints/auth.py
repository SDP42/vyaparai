from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserRead
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: DbSession) -> User:
    return auth_service.register_user(db, data)


@router.post("/login", response_model=Token, summary="Exchange email + password for a token")
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession, settings: AppSettings
) -> Token:
    # OAuth2 form field is called "username"; we treat it as the email address.
    user = auth_service.authenticate(db, form.username, form.password)
    token, expires_in = create_access_token(str(user.id), settings)
    return Token(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user
