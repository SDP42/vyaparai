from collections.abc import Callable

from fastapi.testclient import TestClient

Make = Callable[[str], dict[str, str]]


def _ws(client: TestClient, h: dict[str, str]) -> str:
    r = client.post("/api/v1/workspaces", json={"name": "Shop"}, headers=h)
    return str(r.json()["id"])


def _me(client: TestClient, h: dict[str, str]) -> str:
    return str(client.get("/api/v1/auth/me", headers=h).json()["id"])


def _join(client: TestClient, ws: str, owner: dict[str, str], who: dict[str, str], role: str):
    t = client.post(f"/api/v1/workspaces/{ws}/invitations", json={"role": role}, headers=owner)
    assert t.status_code == 201
    return client.post(
        "/api/v1/invitations/accept", json={"token": t.json()["token"]}, headers=who
    ), t.json()


def test_invite_accept_once_with_fixed_role(client: TestClient, make_user: Make) -> None:
    owner, guest, other = make_user("o@x.com"), make_user("g@x.com"), make_user("h@x.com")
    ws = _ws(client, owner)
    r, inv = _join(client, ws, owner, guest, "analyst")
    assert r.status_code == 200
    members = client.get(f"/api/v1/workspaces/{ws}/members", headers=owner).json()
    assert {m["email"]: m["role"] for m in members}["g@x.com"] == "analyst"
    again = client.post("/api/v1/invitations/accept", json={"token": inv["token"]}, headers=other)
    assert again.status_code == 404  # single use
    listed = client.get(f"/api/v1/workspaces/{ws}/invitations", headers=owner).json()
    assert listed[0]["status"] == "used"
    assert "token" not in listed[0]


def test_revoked_and_unknown_tokens_fail_the_same_way(client: TestClient, make_user: Make) -> None:
    owner, guest = make_user("o@x.com"), make_user("g@x.com")
    ws = _ws(client, owner)
    t = client.post(f"/api/v1/workspaces/{ws}/invitations", json={}, headers=owner).json()
    assert (
        client.delete(f"/api/v1/workspaces/{ws}/invitations/{t['id']}", headers=owner).status_code
        == 204
    )
    a = client.post("/api/v1/invitations/accept", json={"token": t["token"]}, headers=guest)
    b = client.post("/api/v1/invitations/accept", json={"token": "x" * 40}, headers=guest)
    assert a.status_code == b.status_code == 404
    assert a.json()["error"]["message"] == b.json()["error"]["message"]


def test_only_admins_manage_invites_and_admin_cannot_invite_owner(
    client: TestClient, make_user: Make
) -> None:
    owner, admin, viewer = make_user("o@x.com"), make_user("a@x.com"), make_user("v@x.com")
    ws = _ws(client, owner)
    _join(client, ws, owner, admin, "admin")
    _join(client, ws, owner, viewer, "viewer")
    base = f"/api/v1/workspaces/{ws}/invitations"
    assert client.post(base, json={}, headers=viewer).status_code == 403
    assert client.post(base, json={"role": "owner"}, headers=admin).status_code == 403
    assert client.post(base, json={"role": "analyst"}, headers=admin).status_code == 201


def test_change_role_and_last_owner_protected(client: TestClient, make_user: Make) -> None:
    owner, guest = make_user("o@x.com"), make_user("g@x.com")
    ws = _ws(client, owner)
    _join(client, ws, owner, guest, "viewer")
    gid, oid = _me(client, guest), _me(client, owner)
    r = client.patch(
        f"/api/v1/workspaces/{ws}/members/{gid}", json={"role": "analyst"}, headers=owner
    )
    assert r.status_code == 200
    assert r.json()["role"] == "analyst"
    demote = client.patch(
        f"/api/v1/workspaces/{ws}/members/{oid}", json={"role": "admin"}, headers=owner
    )
    assert demote.status_code == 409
    assert client.delete(f"/api/v1/workspaces/{ws}/members/{oid}", headers=owner).status_code == 409


def test_admin_cannot_touch_an_owner(client: TestClient, make_user: Make) -> None:
    owner, admin = make_user("o@x.com"), make_user("a@x.com")
    ws = _ws(client, owner)
    _join(client, ws, owner, admin, "admin")
    oid = _me(client, owner)
    base = f"/api/v1/workspaces/{ws}/members/{oid}"
    assert client.patch(base, json={"role": "viewer"}, headers=admin).status_code == 403
    assert client.delete(base, headers=admin).status_code == 403


def test_removed_member_loses_access(client: TestClient, make_user: Make) -> None:
    owner, guest = make_user("o@x.com"), make_user("g@x.com")
    ws = _ws(client, owner)
    _join(client, ws, owner, guest, "viewer")
    gid = _me(client, guest)
    assert client.delete(f"/api/v1/workspaces/{ws}/members/{gid}", headers=owner).status_code == 204
    assert client.get(f"/api/v1/workspaces/{ws}", headers=guest).status_code == 404
