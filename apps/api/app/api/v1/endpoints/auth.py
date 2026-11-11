"""Sign-in, sessions and registration.

POST /auth/login        email + password -> access token (15 min) and an HttpOnly refresh cookie
POST /auth/refresh      rotate the refresh cookie, get a new access token
POST /auth/logout       revoke this sign-in everywhere it was refreshed
POST /auth/logout-all   revoke every sign-in of the current user
GET  /auth/me           who am I
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.core.config import Settings
from app.core.errors import AppError, AuthenticationError, NotFoundError, PermissionDeniedError
from app.core.ratelimit import Limiter, RateLimitedError, make_limiter
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserRead
from app.services import auth as auth_service
from app.services import demo, personas, sessions

router = APIRouter(prefix="/auth", tags=["auth"])
AUTH_PATH = "/api/v1/auth"  # the refresh cookie is only ever sent here


class TooManyAttemptsError(AppError):
    status_code = 429
    code = "too_many_attempts"

    def __init__(self, retry_after: int) -> None:
        super().__init__(
            f"Too many attempts. Try again in {max(1, retry_after // 60 + 1)} minutes."
        )
        self.retry_after = retry_after


_limiters: dict[str, Limiter] = {}


def limiter(name: str, settings: Settings) -> Limiter:
    if name not in _limiters:
        per = {
            "login": (settings.login_failures_per_window, settings.login_window_seconds),
            "register": (settings.register_per_hour_per_ip, 3600),
        }[name]
        _limiters[name] = make_limiter(name, per[0], per[1], settings.redis_url)
    return _limiters[name]


def reset_limiters() -> None:
    """Forget all counters (used by tests)."""
    _limiters.clear()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def csrf_guard(request: Request, settings: AppSettings) -> None:
    """Cookie endpoints need a header a cross-site page cannot send, and a known origin."""
    if request.headers.get("x-requested-with") != "vyapar":
        raise PermissionDeniedError("Missing the request header that protects sign-in cookies.")
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        raise PermissionDeniedError("This request came from an unknown site.")


def _set_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        settings.refresh_cookie_name,
        token,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=AUTH_PATH,
    )


def _clear_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        settings.refresh_cookie_name, path=AUTH_PATH, httponly=True, samesite="lax"
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: DbSession, request: Request, settings: AppSettings) -> User:
    lim, key = limiter("register", settings), _client_ip(request)
    try:
        lim.check(key)
    except RateLimitedError as exc:
        raise TooManyAttemptsError(exc.retry_after) from exc
    lim.hit(key)
    return auth_service.register_user(db, data)


@router.post("/login", response_model=Token, summary="Exchange email + password for a token")
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
    settings: AppSettings,
    request: Request,
    response: Response,
) -> Token:
    # OAuth2 form field is called "username"; we treat it as the email address.
    lim = limiter("login", settings)
    keys = [f"ip:{_client_ip(request)}", f"acct:{form.username.strip().lower()}"]
    try:
        for k in keys:
            lim.check(k)
    except RateLimitedError as exc:
        raise TooManyAttemptsError(exc.retry_after) from exc
    try:
        user = auth_service.authenticate(db, form.username, form.password)
    except AuthenticationError:
        for k in keys:
            lim.hit(k)  # only failures count
        raise
    lim.reset(keys[1])
    token, expires_in = create_access_token(str(user.id), settings)
    refresh = sessions.issue(db, user, settings, user_agent=request.headers.get("user-agent"))
    db.commit()
    _set_cookie(response, refresh, settings)
    return Token(access_token=token, expires_in=expires_in)


class DemoLogin(BaseModel):
    persona: str


@router.get("/demo-status")
def demo_status(settings: AppSettings) -> dict[str, Any]:
    """Whether one-tap persona sign-in is on, and the personas it offers (public, no data)."""
    if not settings.demo_login_enabled:
        return {"enabled": False, "personas": []}
    return {
        "enabled": True,
        "personas": [
            {
                "key": p.key, "name": demo.NAMES[p.key], "label": p.label, "about": p.about,
                "home": p.home,
            }
            for p in personas.PERSONAS.values()
        ],
    }  # fmt: skip


@router.post("/demo-login", response_model=Token, dependencies=[Depends(csrf_guard)])
def demo_login(
    data: DemoLogin, db: DbSession, settings: AppSettings, request: Request, response: Response
) -> Token:
    if not settings.demo_login_enabled:
        raise NotFoundError("Not found")
    if data.persona not in personas.PERSONAS:
        raise AppError("Unknown persona")
    lim = limiter("login", settings)
    key = f"demo:{_client_ip(request)}"
    try:
        lim.check(key)
    except RateLimitedError as exc:
        raise TooManyAttemptsError(exc.retry_after) from exc
    lim.hit(key)
    user = demo.ensure_persona_user(db, data.persona)
    token, expires_in = create_access_token(str(user.id), settings)
    refresh = sessions.issue(db, user, settings, user_agent=request.headers.get("user-agent"))
    db.commit()
    _set_cookie(response, refresh, settings)
    return Token(access_token=token, expires_in=expires_in)


@router.post("/refresh", response_model=Token, dependencies=[Depends(csrf_guard)])
def refresh(request: Request, response: Response, db: DbSession, settings: AppSettings) -> Token:
    cookie = request.cookies.get(settings.refresh_cookie_name)
    if not cookie:
        raise AuthenticationError("Not signed in")
    try:
        user, new = sessions.rotate(
            db, cookie, settings, user_agent=request.headers.get("user-agent")
        )
    except AuthenticationError:
        _clear_cookie(response, settings)
        raise
    token, expires_in = create_access_token(str(user.id), settings)
    _set_cookie(response, new, settings)
    return Token(access_token=token, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(csrf_guard)])
def logout(request: Request, db: DbSession, settings: AppSettings) -> Response:
    sessions.revoke_by_token(db, request.cookies.get(settings.refresh_cookie_name))
    out = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_cookie(out, settings)
    return out


@router.post(
    "/logout-all", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(csrf_guard)]
)
def logout_all(user: CurrentUser, db: DbSession, settings: AppSettings) -> Response:
    sessions.revoke_all(db, user.id)
    db.commit()
    out = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_cookie(out, settings)
    return out


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user
