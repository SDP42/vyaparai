# ruff: noqa: E501
"""Cost history and margin leaks on a shop whose costs and prices are set by hand.

Windows (as of 25 Oct, 28 days): previous = 28 Sep to 25 Oct is wrong, so: current 28 Sep-25 Oct,
previous 31 Aug-27 Sep. Each product sells 10 units on one day per window.

  OIL   cost 100 -> 120 (+20.0 %), price 150 -> 150 (0.0 %)      margin 33.33 -> 20.00: MARGIN LEAK
        leak = 10 x ((120-100) - (150-150)) = 200; price to restore 33.33 % = 120/0.6667 = 180 (+20.0 %)
  SUGAR cost  40 ->  48 (+20.0 %), price  60 ->  72 (+20.0 %)   margin 33.33 -> 33.33: passed on
  RICE  cost  80 ->  60 (-25.0 %), price 100 -> 100              margin 20.00 -> 40.00: cost down
  SALT  cost  20 ->  20.4 (+2.0 %), price 30 -> 30               under the 3 % threshold: stable
  TEA   sold with no cost recorded                               no_cost
  NEW   only sold in the current window                          new
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.services import costs
from tests.test_intelligence_api import make_shop

D = Decimal
HEAD = "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status"


def row(bill, day, sku, name, qty, rate, cost):
    c = "" if cost is None else str(cost)
    return f"{bill},{day},{sku},{name},Cat,{qty},{rate},0,{c},,,,Store,Paid"


def shop_csv() -> str:
    prev, cur = (
        "10/09/2026",
        "10/10/2026",
    )  # 10 Sep is in the previous window, 10 Oct in the current
    rows = [HEAD]
    spec = [
        ("OIL", "Oil", 100, 150, 120, 150), ("SUG", "Sugar", 40, 60, 48, 72),
        ("RIC", "Rice", 80, 100, 60, 100), ("SAL", "Salt", 20, 30, 20.4, 30),
    ]  # fmt: skip
    for i, (sku, name, c0, p0, c1, p1) in enumerate(spec):
        rows.append(row(f"P{i}", prev, sku, name, 10, p0, c0))
        rows.append(row(f"C{i}", cur, sku, name, 10, p1, c1))
    rows.append(row("PT", prev, "TEA", "Tea", 10, 200, None))
    rows.append(row("CT", cur, "TEA", "Tea", 10, 200, None))
    rows.append(row("CN", cur, "NEW", "New thing", 10, 50, 30))
    rows.append(row("END", "25/10/2026", "SAL", "Salt", 1, 30, 20.4))  # pins as-of to 25 Oct
    return "\n".join(rows) + "\n"


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "cost@shop.in", shop_csv())


def get(client, shop, path, **params):
    return client.get(f"/api/v1/workspaces/{shop[1]}/costs{path}", params=params, headers=shop[0])


# ---------------------------------------------------------------- pure comparison


def win(units, cost, price):
    return costs.Win(D(units), D(units), D(units) * D(price), D(units) * D(cost))


def test_margin_leak_is_detected_with_the_price_that_fixes_it() -> None:
    r = costs.classify(win(10, 100, 150), win(10, 120, 150))
    assert r["status"] == "margin_leak"
    assert r["cost_change_pct"] == D("20.0")
    assert r["margin_prev_pct"] == D("33.33")
    assert r["margin_now_pct"] == D("20.00")
    assert r["leak_amount"] == D("200.00")
    assert r["suggested_price"] == D(180)  # 120 / (1 - 0.3333)
    assert r["suggested_increase_pct"] == D("20.0")


def test_passed_on_cost_down_stable_and_small_samples() -> None:
    assert costs.classify(win(10, 40, 60), win(10, 48, 72))["status"] == "passed_on"
    down = costs.classify(win(10, 80, 100), win(10, 60, 100))
    assert down["status"] == "cost_down"
    assert down["margin_now_pct"] == D("40.00")
    assert costs.classify(win(10, 20, 30), win(10, "20.4", 30))["status"] == "stable"  # +2 %
    assert costs.classify(win(3, 100, 150), win(10, 120, 150))["status"] == "too_few"
    assert costs.classify(None, win(10, 100, 150))["status"] == "new"
    assert costs.classify(win(10, 1, 2), costs.Win(D(10), D(0), D(0), D(0)))["status"] == "no_cost"


def test_a_price_rise_that_keeps_margin_within_a_point_is_not_a_leak() -> None:
    r = costs.classify(
        win(10, 100, 150), win(10, 120, "178.5")
    )  # margin 33.33 -> 32.77, down 0.56 pt
    assert r["status"] == "passed_on"


# ---------------------------------------------------------------- API


def test_overview_matches_hand_computed_values(client: TestClient, shop) -> None:
    r = get(client, shop, "/overview", as_of="2026-10-25").json()
    by = {i["sku"]: i for i in r["items"]}
    assert r["current"] == {"from": "2026-09-28", "to": "2026-10-25"}
    assert r["previous"] == {"from": "2026-08-31", "to": "2026-09-27"}
    oil = by["OIL"]
    assert oil["status"] == "margin_leak"
    assert D(oil["cost_prev"]) == 100
    assert D(oil["cost_now"]) == 120
    assert D(oil["leak_amount"]) == 200
    assert D(oil["suggested_price"]) == 180
    assert by["SUG"]["status"] == "passed_on"
    assert by["RIC"]["status"] == "cost_down"
    assert by["SAL"]["status"] == "stable"
    assert by["TEA"]["status"] == "no_cost"
    assert by["NEW"]["status"] == "new"
    assert r["items"][0]["sku"] == "OIL"  # leaks come first
    s = r["summary"]
    assert s["margin_leaks"] == 1
    assert D(s["leak_amount"]) == 200
    assert s["cost_down"] == 1
    assert s["no_cost"] == 1
    assert s["cost_up"] == 2  # oil and sugar rose 20 %


def test_history_shows_the_cost_step(client: TestClient, shop) -> None:
    r = get(client, shop, "/OIL/history", as_of="2026-10-25", weeks=8).json()
    weeks = [w for w in r["weeks"] if w["cost"] is not None]
    assert [D(w["cost"]) for w in weeks] == [100, 120]  # one sale in each window
    assert [D(w["price"]) for w in weeks] == [150, 150]
    assert len(r["weeks"]) == 8


def test_empty_workspace_and_tenancy(client: TestClient, shop, make_user) -> None:
    h = make_user("e@x.in", "E")
    ws = client.post("/api/v1/workspaces", json={"name": "Empty"}, headers=h).json()["id"]
    r = client.get(f"/api/v1/workspaces/{ws}/costs/overview", headers=h).json()
    assert r["items"] == []
    assert r["as_of"] is None
    stranger = make_user("s@x.in", "S")
    assert (
        client.get(f"/api/v1/workspaces/{shop[1]}/costs/overview", headers=stranger).status_code
        == 404
    )


SAMPLE = (
    __import__("pathlib").Path(__file__).resolve().parents[3]
    / "data"
    / "sample"
    / "vyapar_demo_sales.csv"
)


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample data not generated")
def test_sample_data_finds_the_planted_cost_changes(client: TestClient, make_user) -> None:
    """The sample plants cost rises (oil +7 %, sugar +6 %, toor dal +5 %) with no price change."""
    s = make_shop(client, make_user, "bigcost@shop.in", SAMPLE.read_text())
    r = get(client, s, "/overview", as_of=str(date(2026, 10, 31))).json()
    by = {i["sku"]: i for i in r["items"]}
    assert by["SUG-1KG"]["status"] == "margin_leak"
    assert 5 <= float(by["SUG-1KG"]["cost_change_pct"]) <= 7
    assert abs(float(by["SUG-1KG"]["price_change_pct"])) < 1
    assert r["summary"]["margin_leaks"] >= 1
    assert D(r["summary"]["leak_amount"]) > 0
