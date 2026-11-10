# ruff: noqa: E501
"""Phase 11: headers, size limits, rate limits (memory and Redis), production guards, and hostile uploads."""

import os
import random

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app.core import hardening
from app.core.config import Settings, get_settings
from app.core.ratelimit import RateLimitedError, RedisWindow, SlidingWindow, make_limiter

# ------------------------------------------------------------------ headers


def test_every_api_response_carries_security_headers(client: TestClient) -> None:
    for path in ("/api/v1/health/live", "/api/v1/auth/me", "/nope"):
        h = client.get(path).headers
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY"
        assert h["referrer-policy"] == "no-referrer"
        assert "frame-ancestors 'none'" in h["content-security-policy"]
        assert "camera=()" in h["permissions-policy"]


def test_hsts_only_in_production() -> None:
    from fastapi import Response

    r = Response()
    hardening.apply_headers(r, Settings(app_env="development"))
    assert "strict-transport-security" not in r.headers
    r2 = Response()
    hardening.apply_headers(
        r2, Settings(app_env="test").model_copy(update={"app_env": "production"})
    )
    assert "max-age" in r2.headers["strict-transport-security"]


# ------------------------------------------------------------------ size


def test_oversized_bodies_are_refused_before_they_are_read(client: TestClient) -> None:
    r = client.post(
        "/api/v1/auth/register",
        content=b"x",
        headers={"content-length": str(5 * 1024 * 1024), "content-type": "application/json"},
    )
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "payload_too_large"
    assert r.headers["x-content-type-options"] == "nosniff"


# ------------------------------------------------------------------ rate limits


def test_too_many_requests_get_429_with_retry_after(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 5)
    hardening.reset()
    codes = [client.get("/api/v1/auth/me").status_code for _ in range(8)]
    assert codes[:5] == [401] * 5
    assert set(codes[5:]) == {429}
    r = client.get("/api/v1/auth/me")
    assert r.json()["error"]["code"] == "rate_limited"
    assert int(r.headers["retry-after"]) >= 1
    assert client.get("/api/v1/health/live").status_code == 200  # probes are never limited


def test_expensive_endpoints_have_a_tighter_limit(
    client: TestClient, make_user, monkeypatch
) -> None:
    h = make_user("rl@shop.in")
    ws = client.post("/api/v1/workspaces", json={"name": "Shop"}, headers=h).json()["id"]
    monkeypatch.setattr(get_settings(), "heavy_rate_limit_per_minute", 3)
    hardening.reset()
    codes = [
        client.post(
            f"/api/v1/workspaces/{ws}/assistant/ask", json={"question": "sales"}, headers=h
        ).status_code
        for _ in range(5)
    ]
    assert codes[:3] == [200] * 3
    assert codes[3:] == [429, 429]
    assert (
        client.get(f"/api/v1/workspaces/{ws}/alerts", headers=h).status_code == 200
    )  # reads are not "heavy"


def test_the_client_address_is_only_trusted_behind_a_proxy(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 2)
    hardening.reset()
    for i in range(4):  # spoofed header ignored: still one address
        r = client.get("/api/v1/auth/me", headers={"x-forwarded-for": f"9.9.9.{i}"})
    assert r.status_code == 429
    monkeypatch.setattr(get_settings(), "trust_proxy", True)
    hardening.reset()
    assert [
        client.get("/api/v1/auth/me", headers={"x-forwarded-for": f"9.9.9.{i}"}).status_code
        for i in range(4)
    ] == [401] * 4


# ------------------------------------------------------------------ redis window


def test_redis_window_shares_counts_and_expires() -> None:
    now = [1000.0]
    r = fakeredis.FakeRedis()
    a = RedisWindow(r, "t", 3, 60, clock=lambda: now[0])
    b = RedisWindow(r, "t", 3, 60, clock=lambda: now[0])  # a second process
    for _ in range(3):
        a.hit("ip")
    with pytest.raises(RateLimitedError) as e:
        b.check("ip")
    assert 1 <= e.value.retry_after <= 61
    now[0] += 61
    b.check("ip")  # the window has passed
    b.hit("ip")
    b.reset("ip")
    b.check("ip")


def test_redis_window_fails_open_when_the_store_is_down() -> None:
    class Down:
        def __getattr__(self, name):
            raise ConnectionError("redis is down")

    w = RedisWindow(Down(), "t", 1, 60)
    w.hit("x")
    w.check("x")  # no exception: the product stays up
    w.reset("x")


def test_memory_window_is_used_without_redis_and_matches_the_interface() -> None:
    w = make_limiter("t", 2, 60)
    assert isinstance(w, SlidingWindow)
    w.hit("a")
    w.hit("a")
    with pytest.raises(RateLimitedError):
        w.check("a")


# ------------------------------------------------------------------ production guards


def test_production_refuses_unsafe_settings() -> None:
    base = {
        "app_env": "production",
        "jwt_secret_key": "x" * 40,
        "database_url": "postgresql+psycopg://u:p@db/x",
    }
    Settings(
        **base, cors_origins=["https://app.example.in"], app_url="https://app.example.in"
    )  # a valid one
    for bad, msg in [
        ({"jwt_secret_key": "short"}, "JWT_SECRET_KEY"),
        ({"database_url": "sqlite:///x.db"}, "PostgreSQL"),
        ({"cors_origins": ["http://app.example.in"], "app_url": "https://app.example.in"}, "https"),
        (
            {"cors_origins": ["https://app.example.in"], "app_url": "http://app.example.in"},
            "APP_URL",
        ),
    ]:
        with pytest.raises(ValueError, match=msg):
            Settings(
                **{
                    **base,
                    "cors_origins": ["https://app.example.in"],
                    "app_url": "https://app.example.in",
                    **bad,
                }
            )


# ------------------------------------------------------------------ hostile uploads: never a 500


def _junk() -> list[tuple[str, bytes]]:
    rng = random.Random(9)  # noqa: S311  (test data)
    return [
        ("empty.csv", b""),
        ("nul.csv", b"\x00" * 2048),
        ("binary.csv", bytes(rng.randrange(256) for _ in range(4096))),
        ("long-line.csv", b"a," * 200_000 + b"\n1,2\n"),
        ("only-header.csv", b"Date,Name,Amount\n"),
        ("quotes.csv", b'"""",""",\n"unterminated,field\n1,2\n'),
        ("utf16.csv", "Date,Name\n2026-01-01,Ram\n".encode("utf-16")),
        ("emoji.csv", "Date,Review\n2026-01-01,😀😡👍\n".encode()),
        ("fake.pdf", b"%PDF-1.4\n" + b"\xff" * 500),
        ("fake.docx", b"PK\x03\x04" + b"\x00" * 100),
        ("bomb.docx", b"PK\x05\x06" + b"\x00" * 18),
        ("script.txt", b"<script>alert(1)</script>\n\n'; DROP TABLE users; --"),
        ("traversal..csv", b"a,b\n1,2\n"),
    ]


@pytest.mark.parametrize(
    "path",
    [
        "reviews/import",
        "udhaar/import",
        "campaigns/contacts/import",
        "inventory/import",
        "bills",
        "documents",
    ],
)
def test_hostile_files_are_refused_or_handled_never_a_server_error(
    client: TestClient, make_user, path: str
) -> None:
    h = make_user("fz@shop.in")
    ws = client.post("/api/v1/workspaces", json={"name": "Shop"}, headers=h).json()["id"]
    for name, data in _junk():
        r = client.post(f"/api/v1/workspaces/{ws}/{path}", files={"file": (name, data)}, headers=h)
        assert r.status_code < 500, (path, name, r.status_code, r.text[:200])


def test_hostile_files_on_the_dataset_upload_flow(client: TestClient, make_user) -> None:
    h = make_user("fz2@shop.in")
    ws = client.post("/api/v1/workspaces", json={"name": "Shop"}, headers=h).json()["id"]
    for name, data in _junk():
        r = client.post(
            f"/api/v1/workspaces/{ws}/datasets", files={"file": (name, data)}, headers=h
        )
        assert r.status_code < 500, (name, r.status_code, r.text[:200])


def test_injection_strings_in_text_fields_are_stored_as_text(client: TestClient, make_user) -> None:
    h = make_user("inj@shop.in")
    ws = client.post("/api/v1/workspaces", json={"name": "Shop'; DROP TABLE users;--"}, headers=h)
    assert ws.status_code == 201
    assert ws.json()["name"].startswith("Shop'; DROP")
    assert client.get("/api/v1/workspaces", headers=h).status_code == 200  # the tables still exist
    q = client.post(
        f"/api/v1/workspaces/{ws.json()['id']}/assistant/ask",
        json={"question": "' OR 1=1 --"},
        headers=h,
    )
    assert q.status_code == 200


def test_no_secret_looking_values_leak_into_errors(client: TestClient) -> None:
    r = client.post(
        "/api/v1/auth/login", data={"username": "nobody@x.in", "password": "wrong-password-1"}
    )
    assert r.status_code == 401
    body = r.text.lower()
    assert "traceback" not in body
    assert "sqlalchemy" not in body
    assert os.environ.get("JWT_SECRET_KEY", "zzzz") not in body
