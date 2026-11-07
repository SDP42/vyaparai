from fastapi.testclient import TestClient

from tests.conftest import PASSWORD


def test_register_login_me(client: TestClient, make_user) -> None:
    headers = make_user("Owner@Example.com", "Asha Shah")
    r = client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "owner@example.com"  # normalised
    assert "hashed_password" not in r.json()


def test_duplicate_email_conflicts(client: TestClient, make_user) -> None:
    make_user("dup@example.com")
    r = client.post("/api/v1/auth/register",
                    json={"email": "DUP@example.com", "full_name": "X", "password": PASSWORD})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_short_password_rejected(client: TestClient) -> None:
    r = client.post("/api/v1/auth/register",
                    json={"email": "a@example.com", "full_name": "A", "password": "short"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_wrong_password_and_unknown_user_look_identical(client: TestClient, make_user) -> None:
    make_user("real@example.com")
    wrong = client.post("/api/v1/auth/login",
                        data={"username": "real@example.com", "password": "nope-nope-nope"})
    missing = client.post("/api/v1/auth/login",
                          data={"username": "ghost@example.com", "password": "nope-nope-nope"})
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json()["error"]["message"] == missing.json()["error"]["message"]


def test_me_requires_token(client: TestClient) -> None:
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_garbage_token_rejected(client: TestClient) -> None:
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401
