"""Personas: who may ask what, what each may open, and one-tap demo sign-in."""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.services import personas
from app.services.assistant import nlu
from app.services.assistant.service import SUGGESTIONS

Make = Callable[[str], dict[str, str]]
CSRF = {"X-Requested-With": "vyapar"}


def _shop(client: TestClient, owner: dict[str, str]) -> str:
    return str(client.post("/api/v1/workspaces", json={"name": "Shop"}, headers=owner).json()["id"])


def _member(
    client: TestClient, ws: str, owner: dict[str, str], who: dict[str, str], role: str, persona: str
) -> None:
    inv = client.post(
        f"/api/v1/workspaces/{ws}/invitations",
        json={"role": role, "persona": persona},
        headers=owner,
    )
    assert inv.status_code == 201, inv.text
    ok = client.post("/api/v1/invitations/accept", json={"token": inv.json()["token"]}, headers=who)
    assert ok.status_code == 200


def _ask(client: TestClient, ws: str, h: dict[str, str], q: str) -> dict[str, Any]:
    r = client.post(f"/api/v1/workspaces/{ws}/assistant/ask", json={"question": q}, headers=h)
    assert r.status_code == 200, r.text
    out: dict[str, Any] = r.json()
    return out


def test_every_intent_is_classified_for_every_persona() -> None:
    """A new intent must be a deliberate allow or deny for each persona, never silently open."""
    for p in personas.PERSONAS.values():
        assert p.intents <= personas.ALL_INTENTS, p.key
        assert {"help", "unknown"} <= p.intents
    nlu_intents = set(nlu.INTENTS) | {"help", "unknown"}
    assert nlu_intents <= personas.ALL_INTENTS | {"product_sales"}, (
        nlu_intents - personas.ALL_INTENTS
    )
    assert personas.PERSONAS["owner"].intents == personas.ALL_INTENTS


def test_persona_text_exists_in_every_language_and_nav_is_valid() -> None:
    for p in personas.PERSONAS.values():
        for lang in ("en", "hinglish", "hi"):
            assert p.label[lang] and p.about[lang] and len(p.suggestions[lang]) == 5, (p.key, lang)
        assert all(x.startswith("/app") for x in p.nav)
    assert set(SUGGESTIONS) == {"en", "hinglish", "hi"}


def test_cashier_cannot_ask_for_profit_or_credit_but_owner_can(
    client: TestClient, make_user: Make
) -> None:
    owner, staff = make_user("o@x.com"), make_user("c@x.com")
    ws = _shop(client, owner)
    _member(client, ws, owner, staff, "viewer", "cashier")
    for q in ("What is my margin?", "Who owes me money?", "Why did sales drop?"):
        out = _ask(client, ws, staff, q)
        assert out["refused"] is True and out["rows"] == []
        assert out["suggestions"] == list(personas.PERSONAS["cashier"].suggestions["en"])
        assert _ask(client, ws, owner, q).get("refused") is None


def test_refusal_is_localized(client: TestClient, make_user: Make) -> None:
    owner, staff = make_user("o@x.com"), make_user("c@x.com")
    ws = _shop(client, owner)
    _member(client, ws, owner, staff, "viewer", "cashier")
    out = _ask(client, ws, staff, "मार्जिन कितना है?")
    assert out["refused"] is True and out["language"] == "hi"
    assert "मालिक" in out["answer"]


def test_member_without_persona_keeps_role_access(client: TestClient, make_user: Make) -> None:
    owner, guest = make_user("o@x.com"), make_user("g@x.com")
    ws = _shop(client, owner)
    inv = client.post(
        f"/api/v1/workspaces/{ws}/invitations", json={"role": "viewer"}, headers=owner
    )
    client.post("/api/v1/invitations/accept", json={"token": inv.json()["token"]}, headers=guest)
    assert _ask(client, ws, guest, "What is my margin?").get("refused") is None
    me = client.get(f"/api/v1/workspaces/{ws}/me", headers=guest).json()
    assert me["persona"] is None and me["restricted"] is False


def test_capability_blocks_sensitive_endpoints(client: TestClient, make_user: Make) -> None:
    owner, staff, acct = make_user("o@x.com"), make_user("c@x.com"), make_user("a@x.com")
    ws = _shop(client, owner)
    _member(client, ws, owner, staff, "viewer", "cashier")
    _member(client, ws, owner, acct, "viewer", "accountant")
    base = f"/api/v1/workspaces/{ws}"
    assert client.get(f"{base}/udhaar/summary", headers=staff).status_code == 403
    assert client.get(f"{base}/udhaar/summary", headers=acct).status_code != 403
    assert client.get(f"{base}/bills", headers=staff).status_code == 403
    assert client.get(f"{base}/costs/overview", headers=staff).status_code == 403
    assert client.get(f"{base}/udhaar/summary", headers=owner).status_code != 403


def test_persona_must_fit_the_role(client: TestClient, make_user: Make) -> None:
    owner = make_user("o@x.com")
    ws = _shop(client, owner)
    for role, persona in (("viewer", "owner"), ("viewer", "analyst"), ("analyst", "bogus")):
        r = client.post(
            f"/api/v1/workspaces/{ws}/invitations",
            json={"role": role, "persona": persona},
            headers=owner,
        )
        assert r.status_code == 400, (role, persona)


def test_changing_role_clears_a_persona_that_no_longer_fits(
    client: TestClient, make_user: Make
) -> None:
    owner, staff = make_user("o@x.com"), make_user("c@x.com")
    ws = _shop(client, owner)
    _member(client, ws, owner, staff, "admin", "ops_manager")
    uid = client.get("/api/v1/auth/me", headers=staff).json()["id"]
    r = client.patch(
        f"/api/v1/workspaces/{ws}/members/{uid}", json={"role": "viewer"}, headers=owner
    )
    assert r.status_code == 200 and r.json()["persona"] is None
    r = client.patch(
        f"/api/v1/workspaces/{ws}/members/{uid}",
        json={"role": "viewer", "persona": "cashier"},
        headers=owner,
    )
    assert r.json()["persona"] == "cashier"


def test_my_view_lists_pages_and_suggestions(client: TestClient, make_user: Make) -> None:
    owner, staff = make_user("o@x.com"), make_user("c@x.com")
    ws = _shop(client, owner)
    _member(client, ws, owner, staff, "viewer", "cashier")
    me = client.get(f"/api/v1/workspaces/{ws}/me?lang=hi", headers=staff).json()
    assert me["persona"]["key"] == "cashier" and me["persona"]["label"] == "काउंटर स्टाफ"
    assert "/app/udhaar" not in me["persona"]["nav"] and "/app/ask" in me["persona"]["nav"]


@pytest.fixture
def demo_on(client: TestClient) -> Iterator[None]:
    app = client.app
    app.dependency_overrides[get_settings] = lambda: Settings(  # type: ignore[attr-defined]
        app_env="test", demo_login_enabled=True
    )
    yield
    app.dependency_overrides.pop(get_settings, None)  # type: ignore[attr-defined]


def test_demo_login_off_by_default(client: TestClient) -> None:
    assert client.get("/api/v1/auth/demo-status").json() == {"enabled": False, "personas": []}
    r = client.post("/api/v1/auth/demo-login", json={"persona": "owner"}, headers=CSRF)
    assert r.status_code == 404


def test_demo_login_signs_in_each_persona_to_one_shop(client: TestClient, demo_on: None) -> None:
    assert len(client.get("/api/v1/auth/demo-status").json()["personas"]) == 5
    shops = set()
    for key in personas.PERSONAS:
        r = client.post("/api/v1/auth/demo-login", json={"persona": key}, headers=CSRF)
        assert r.status_code == 200, r.text
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        (ws,) = client.get("/api/v1/workspaces", headers=h).json()
        shops.add(ws["id"])
        me = client.get(f"/api/v1/workspaces/{ws['id']}/me", headers=h).json()
        assert me["persona"]["key"] == key
    assert len(shops) == 1
    bad = client.post("/api/v1/auth/demo-login", json={"persona": "god"}, headers=CSRF)
    assert bad.status_code == 400


def test_demo_login_cannot_be_enabled_in_production() -> None:
    with pytest.raises(ValueError, match="DEMO_LOGIN_ENABLED"):
        Settings(
            app_env="production",
            demo_login_enabled=True,
            jwt_secret_key="x" * 40,
            database_url="postgresql://u:p@h/db",
            cors_origins=["https://a.example"],
            app_url="https://a.example",
        )
