"""Sales by the person on the bill, and counter staff seeing only their own."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.test_intelligence_api import make_shop


def staff_csv() -> str:
    start = date(2026, 8, 3)
    lines = ["Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Cashier"]
    for i in range(20):
        day = (start + timedelta(days=i)).strftime("%d/%m/%Y")
        who = "Sunita  Patil" if i % 2 == 0 else "Ravi"  # a double space, tidied on import
        lines.append(f"A{i},{day},SKU-A,Atta,Staples,2,100,0,60,{who}")
        lines.append(f"B{i},{day},SKU-B,Rice,Staples,1,300,10,200,{who}")
        if i % 5 == 0:
            lines.append(f"C{i},{day},SKU-C,Ghee,Dairy,1,600,0,450,")  # no cashier on this bill
    return "\n".join(lines) + "\n"


def _join(client: TestClient, ws, owner, who, role, persona, staff_name=None):
    inv = client.post(
        f"/api/v1/workspaces/{ws}/invitations",
        json={"role": role, "persona": persona},
        headers=owner,
    )
    client.post("/api/v1/invitations/accept", json={"token": inv.json()["token"]}, headers=who)
    if staff_name:
        uid = client.get("/api/v1/auth/me", headers=who).json()["id"]
        r = client.patch(
            f"/api/v1/workspaces/{ws}/members/{uid}",
            json={"role": role, "persona": persona, "staff_name": staff_name},
            headers=owner,
        )
        assert r.status_code == 200
        assert r.json()["staff_name"] == staff_name


def test_staff_sales_are_grouped_by_the_name_on_the_bill(client: TestClient, make_user) -> None:
    owner, ws = make_shop(client, make_user, "s@shop.in", staff_csv())
    out = client.get(f"/api/v1/workspaces/{ws}/analytics/staff", headers=owner).json()
    rows = {r["staff"]: r for r in out["rows"]}
    assert out["has_staff"] is True
    assert set(rows) == {"Sunita Patil", "Ravi", "Unspecified"}
    assert rows["Sunita Patil"]["orders"] == 20  # 10 days, two bills each
    assert rows["Ravi"]["orders"] == 20
    assert rows["Unspecified"]["orders"] == 4
    assert abs(sum(float(r["share"]) for r in out["rows"]) - 100) < 0.01
    assert rows["Ravi"]["margin_pct"] is not None


def test_no_staff_column_says_so(client: TestClient, make_user) -> None:
    from tests.test_forecast_api import shop_csv

    owner, ws = make_shop(client, make_user, "n@shop.in", shop_csv(30))
    out = client.get(f"/api/v1/workspaces/{ws}/analytics/staff", headers=owner).json()
    assert out["has_staff"] is False
    assert "Map that column" in out["note"]


def test_counter_staff_see_only_their_own_row_and_no_margin(client: TestClient, make_user) -> None:
    owner, ws = make_shop(client, make_user, "o@shop.in", staff_csv())
    cashier, ops = make_user("c@shop.in"), make_user("m@shop.in")
    _join(
        client, ws, owner, cashier, "viewer", "cashier", staff_name="ravi"
    )  # case does not matter
    _join(client, ws, owner, ops, "admin", "ops_manager")
    base = f"/api/v1/workspaces/{ws}/analytics/staff"
    own = client.get(base, headers=cashier).json()
    assert own["own_only"] is True
    assert [r["staff"] for r in own["rows"]] == ["Ravi"]
    assert own["rows"][0]["margin_pct"] is None  # a cashier does not see margin
    all_rows = client.get(base, headers=ops).json()
    assert {r["staff"] for r in all_rows["rows"]} == {"Sunita Patil", "Ravi", "Unspecified"}
    assert all(r["margin_pct"] is None for r in all_rows["rows"])  # nor does operations


def test_unlinked_counter_staff_are_told_to_ask_the_owner(client: TestClient, make_user) -> None:
    owner, ws = make_shop(client, make_user, "u@shop.in", staff_csv())
    cashier = make_user("cu@shop.in")
    _join(client, ws, owner, cashier, "viewer", "cashier")
    out = client.get(f"/api/v1/workspaces/{ws}/analytics/staff", headers=cashier).json()
    assert out["rows"] == [] and out["needs_link"] is True


def test_accountant_cannot_open_staff_sales(client: TestClient, make_user) -> None:
    owner, ws = make_shop(client, make_user, "a@shop.in", staff_csv())
    acct = make_user("ac@shop.in")
    _join(client, ws, owner, acct, "viewer", "accountant")
    assert client.get(f"/api/v1/workspaces/{ws}/analytics/staff", headers=acct).status_code == 403
