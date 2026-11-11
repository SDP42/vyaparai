from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.session import RefreshToken
from tests.conftest import PASSWORD

CSRF = {"X-Requested-With": "vyapar"}
EMAIL = "sess@example.com"


def _login(client: TestClient, email: str = EMAIL, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", data={"username": email, "password": password})


@pytest.fixture
def user(client: TestClient) -> str:
    r = client.post(
        "/api/v1/auth/register", json={"email": EMAIL, "full_name": "S", "password": PASSWORD}
    )
    assert r.status_code == 201
    return EMAIL


def test_login_sets_httponly_cookie_scoped_to_auth(client: TestClient, user: str) -> None:
    r = _login(client)
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert "vyapar_refresh=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/api/v1/auth" in cookie
    assert (
        r.json()["expires_in"] == get_settings().access_token_expire_minutes * 60
    )  # short-lived whatever .env says
    assert get_settings().access_token_expire_minutes <= 30


def test_refresh_rotates_and_issues_new_access_token(client: TestClient, user: str) -> None:
    _login(client)
    old = client.cookies.get("vyapar_refresh")
    r = client.post("/api/v1/auth/refresh", headers=CSRF)
    assert r.status_code == 200
    assert client.cookies.get("vyapar_refresh") != old
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


def test_refresh_needs_csrf_header_and_known_origin(client: TestClient, user: str) -> None:
    _login(client)
    assert client.post("/api/v1/auth/refresh").status_code == 403
    bad = client.post("/api/v1/auth/refresh", headers={**CSRF, "Origin": "https://evil.example"})
    assert bad.status_code == 403
    ok = client.post("/api/v1/auth/refresh", headers={**CSRF, "Origin": "http://localhost:3000"})
    assert ok.status_code == 200


def test_refresh_without_cookie_is_401(client: TestClient) -> None:
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401


def test_reusing_an_old_token_revokes_the_family(
    client: TestClient, user: str, db_session_factory: sessionmaker[Session]
) -> None:
    _login(client)
    stolen = client.cookies.get("vyapar_refresh")
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 200
    # age the first token past the grace window
    with db_session_factory() as db:
        for row in db.scalars(select(RefreshToken).where(RefreshToken.used_at.is_not(None))):
            row.used_at = datetime.now(UTC) - timedelta(minutes=5)
        db.commit()
    client.cookies.clear()
    client.cookies.set("vyapar_refresh", stolen, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401
    # the legitimate newer token is dead too
    with db_session_factory() as db:
        assert all(r.revoked_at is not None for r in db.scalars(select(RefreshToken)))


def test_two_tabs_refreshing_at_once_are_tolerated(client: TestClient, user: str) -> None:
    _login(client)
    same = client.cookies.get("vyapar_refresh")
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 200
    client.cookies.clear()
    client.cookies.set("vyapar_refresh", same, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 200


def test_idle_expiry(
    client: TestClient, user: str, db_session_factory: sessionmaker[Session]
) -> None:
    _login(client)
    with db_session_factory() as db:
        for row in db.scalars(select(RefreshToken)):
            row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401


def test_absolute_lifetime_caps_expiry(
    client: TestClient, user: str, db_session_factory: sessionmaker[Session]
) -> None:
    _login(client)
    with db_session_factory() as db:
        for row in db.scalars(select(RefreshToken)):
            row.family_started_at = datetime.now(UTC) - timedelta(days=29, hours=23)
        db.commit()
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 200
    with db_session_factory() as db:
        newest = db.scalars(select(RefreshToken).order_by(RefreshToken.created_at.desc())).first()
        assert newest is not None
        exp = (
            newest.expires_at if newest.expires_at.tzinfo else newest.expires_at.replace(tzinfo=UTC)
        )
        assert exp < datetime.now(UTC) + timedelta(hours=2)


def test_logout_revokes_and_clears(client: TestClient, user: str) -> None:
    _login(client)
    assert client.post("/api/v1/auth/logout", headers=CSRF).status_code == 204
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401


def test_logout_all_revokes_other_devices(client: TestClient, user: str) -> None:
    a = _login(client).json()["access_token"]
    first = client.cookies.get("vyapar_refresh")
    _login(client)
    r = client.post("/api/v1/auth/logout-all", headers={**CSRF, "Authorization": f"Bearer {a}"})
    assert r.status_code == 204
    client.cookies.clear()
    client.cookies.set("vyapar_refresh", first, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401


def test_login_is_throttled_after_repeated_failures(client: TestClient, user: str) -> None:
    for _ in range(5):
        assert _login(client, password="wrong-password-1").status_code == 401
    r = _login(client, password="wrong-password-1")
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "too_many_attempts"
    assert _login(client).status_code == 429  # even the right password waits


def test_success_resets_the_account_counter(client: TestClient, user: str) -> None:
    for _ in range(3):
        _login(client, password="wrong-password-1")
    assert _login(client).status_code == 200
    for _ in range(2):  # the per-IP count is separate and is not reset
        assert _login(client, password="wrong-password-1").status_code == 401


def test_register_is_throttled_per_ip(client: TestClient) -> None:
    codes = [
        client.post(
            "/api/v1/auth/register",
            json={"email": f"u{i}@example.com", "full_name": "U", "password": PASSWORD},
        ).status_code
        for i in range(12)
    ]
    assert codes[:10] == [201] * 10
    assert codes[10:] == [429, 429]
