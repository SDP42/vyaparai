"""Tenant-boundary tests: a user must never see or change another workspace's data."""

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def two_tenants(client: TestClient, make_user):
    alice = make_user("alice@example.com", "Alice")
    bob = make_user("bob@example.com", "Bob")
    ws_a = client.post("/api/v1/workspaces", json={"name": "Alice Kirana"}, headers=alice).json()
    ws_b = client.post("/api/v1/workspaces", json={"name": "Bob Textiles"}, headers=bob).json()
    return alice, bob, ws_a, ws_b


def test_creator_becomes_owner(client: TestClient, two_tenants) -> None:
    alice, _, ws_a, _ = two_tenants
    r = client.get(f"/api/v1/workspaces/{ws_a['id']}", headers=alice)
    assert r.status_code == 200
    assert r.json()["role"] == "owner"
    assert r.json()["currency"] == "INR"


def test_list_only_shows_own_workspaces(client: TestClient, two_tenants) -> None:
    alice, _, ws_a, _ = two_tenants
    ids = [w["id"] for w in client.get("/api/v1/workspaces", headers=alice).json()]
    assert ids == [ws_a["id"]]


@pytest.mark.parametrize(
    "path",
    ["", "/members", "/datasets", f"/datasets/{uuid.uuid4()}", f"/jobs/{uuid.uuid4()}"],
)
def test_non_member_gets_404_not_403(client: TestClient, two_tenants, path: str) -> None:
    alice, _, _, ws_b = two_tenants
    r = client.get(f"/api/v1/workspaces/{ws_b['id']}{path}", headers=alice)
    assert r.status_code == 404
    assert r.json()["error"]["message"] == "Workspace not found"


def test_non_member_cannot_update(client: TestClient, two_tenants) -> None:
    alice, _, _, ws_b = two_tenants
    r = client.patch(f"/api/v1/workspaces/{ws_b['id']}", json={"name": "Hacked"}, headers=alice)
    assert r.status_code == 404


def test_viewer_cannot_admin(client: TestClient, two_tenants, make_user) -> None:
    alice, _, ws_a, _ = two_tenants
    viewer = make_user("viewer@example.com")
    r = client.post(
        f"/api/v1/workspaces/{ws_a['id']}/members",
        json={"email": "viewer@example.com", "role": "viewer"},
        headers=alice,
    )
    assert r.status_code == 201

    assert client.get(f"/api/v1/workspaces/{ws_a['id']}", headers=viewer).status_code == 200
    r = client.patch(f"/api/v1/workspaces/{ws_a['id']}", json={"name": "Nope"}, headers=viewer)
    assert r.status_code == 403
    r = client.get(f"/api/v1/workspaces/{ws_a['id']}/audit-logs", headers=viewer)
    assert r.status_code == 403


def test_admin_cannot_grant_owner(client: TestClient, two_tenants, make_user) -> None:
    alice, _, ws_a, _ = two_tenants
    admin = make_user("admin@example.com")
    make_user("third@example.com")
    client.post(
        f"/api/v1/workspaces/{ws_a['id']}/members",
        json={"email": "admin@example.com", "role": "admin"},
        headers=alice,
    )
    r = client.post(
        f"/api/v1/workspaces/{ws_a['id']}/members",
        json={"email": "third@example.com", "role": "owner"},
        headers=admin,
    )
    assert r.status_code == 403


def test_audit_log_records_actions(client: TestClient, two_tenants) -> None:
    alice, _, ws_a, _ = two_tenants
    client.patch(f"/api/v1/workspaces/{ws_a['id']}", json={"name": "Alice Mart"}, headers=alice)
    r = client.get(f"/api/v1/workspaces/{ws_a['id']}/audit-logs", headers=alice)
    actions = {e["action"] for e in r.json()["items"]}
    assert {"workspace.created", "workspace.updated"} <= actions


def test_empty_dataset_list_is_paginated(client: TestClient, two_tenants) -> None:
    alice, _, ws_a, _ = two_tenants
    r = client.get(f"/api/v1/workspaces/{ws_a['id']}/datasets", headers=alice)
    assert r.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}
