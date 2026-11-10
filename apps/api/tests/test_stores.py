# ruff: noqa: E501
"""Multi-store: compare the workspaces a person belongs to, and nobody else's."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.test_ingestion import full_flow
from tests.test_team import _join

HEAD = "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status\n"


def sales(price_late: int, cost: int, days: int = 60) -> bytes:
    """Steady sales for the first half, then ``price_late`` per unit (to make one store fall or rise)."""
    start = date(2026, 9, 1)
    rows = []
    for i in range(days):
        d = (start + timedelta(days=i)).strftime("%d/%m/%Y")
        rate = 100 if i < days // 2 else price_late
        rows.append(f"S{i},{d},SKU,Tea,Cat,10,{rate},0,{cost},C1,MH,Pune,Store,Paid")
    return (HEAD + "\n".join(rows) + "\n").encode()


def store(client: TestClient, h, name: str, content: bytes) -> str:
    ws = client.post("/api/v1/workspaces", json={"name": name}, headers=h).json()["id"]
    _, base, _ = full_flow(client, h, ws, content)
    client.post(f"{base}/import", headers=h)
    return str(ws)


def test_stores_are_compared_on_rates_with_flags_for_the_ones_that_need_attention(
    client: TestClient, make_user
) -> None:
    h = make_user("multi@shop.in")
    steady = store(client, h, "Steady Store", sales(100, 60))
    falling = store(
        client, h, "Falling Store", sales(70, 60)
    )  # price cut in the second half: sales and margin fall
    r = client.get("/api/v1/stores/overview", headers=h).json()
    by = {s["name"]: s for s in r["stores"]}
    assert set(by) == {"Steady Store", "Falling Store"}
    assert by["Steady Store"]["id"] == steady
    assert by["Steady Store"]["growth_pct"] == 0 or abs(by["Steady Store"]["growth_pct"]) < 1
    assert by["Falling Store"]["growth_pct"] < -10
    assert any("Sales down" in f for f in by["Falling Store"]["flags"])
    assert any("under your stores' average" in f for f in by["Falling Store"]["flags"])
    assert by["Steady Store"]["flags"] == []
    assert r["stores"][0]["name"] == "Falling Store"  # needs-attention first
    assert r["totals"]["needs_attention"] == 1
    assert r["totals"]["stores"] == 2
    assert falling in {s["id"] for s in r["stores"]}


def test_a_person_sees_only_their_own_stores(client: TestClient, make_user) -> None:
    owner, other = make_user("a@shop.in"), make_user("b@shop.in")
    store(client, owner, "Mine", sales(100, 60))
    store(client, other, "Theirs", sales(100, 60))
    names = [
        s["name"] for s in client.get("/api/v1/stores/overview", headers=owner).json()["stores"]
    ]
    assert names == ["Mine"]


def test_a_store_you_were_invited_to_is_included_with_your_role(
    client: TestClient, make_user
) -> None:
    owner, staff = make_user("o@shop.in"), make_user("s@shop.in")
    ws = store(client, owner, "Shared", sales(100, 60))
    _join(client, ws, owner, staff, "viewer")
    mine = store(client, staff, "Own Store", sales(100, 60))
    r = client.get("/api/v1/stores/overview", headers=staff).json()
    roles = {s["name"]: s["role"] for s in r["stores"]}
    assert roles == {"Shared": "viewer", "Own Store": "owner"}
    assert mine in {s["id"] for s in r["stores"]}


def test_different_data_dates_are_called_out_and_a_common_period_aligns_them(
    client: TestClient, make_user
) -> None:
    h = make_user("d@shop.in")
    store(client, h, "Long", sales(100, 60, days=60))
    store(client, h, "Short", sales(100, 60, days=40))
    r = client.get("/api/v1/stores/overview", headers=h).json()
    assert any("different latest sale dates" in n for n in r["notes"])
    same = client.get("/api/v1/stores/overview?from=2026-09-10&to=2026-10-09", headers=h).json()
    assert {s["to"] for s in same["stores"]} == {"2026-10-09"}
    assert not any("different latest sale dates" in n for n in same["notes"])


def test_an_empty_store_and_a_single_store_are_handled(client: TestClient, make_user) -> None:
    h = make_user("e@shop.in")
    client.post("/api/v1/workspaces", json={"name": "Brand New"}, headers=h)
    r = client.get("/api/v1/stores/overview", headers=h).json()
    assert r["stores"][0]["has_data"] is False
    assert "No sales imported yet" in r["stores"][0]["flags"]
    assert any("one store" in n for n in r["notes"])
    assert client.get("/api/v1/stores/overview").status_code == 401
