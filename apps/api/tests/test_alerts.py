# ruff: noqa: E501
"""Alert rules on a shop built so every threshold can be checked by hand.

Product A (rate 100, cost 60) sells 10 units a day from 31 Aug to 24 Oct, except on Sundays
(30 Aug..11 Oct units 10, 12, 8, 10, 10, 9, 11; 18 Oct 10). From 19 Oct a 10 % discount is given.
Sun 25 Oct (the last day): 4 units, discounted: net 360.

Sales on the 8 Sundays before 25 Oct (net): 1000, 1200, 800, 1150 (+150 salt), 1000, 1050 (+150 salt), 1100, 1000.
  sorted 800 1000 1000 1000 1050 1100 1150 1200 -> median 1025, MAD 50, sigma 74.13
  change = (360-1025)/1025 = -64.9 %, z = -8.97                       -> sales_drop, HIGH
Weeks (7-day nets) before: 7000, 7100+750(oil), 6900+600(salt), 7000+450+150(salt); mean 7487.5
  last 7 days: 6 x 1000 + 400 - 640 discount = 5760 -> -23.1 %         -> week_drop, MEDIUM
Discount rate last 7 days 640/6400 = 10.0 % vs 0.0 % before           -> discount_creep, HIGH (+10 pts)
OIL (5 units 10 Sep at cost 100, 5 units 10 Oct at cost 120, price 150): cost +20 %, price 0 %
  margin 33.33 -> 20.00 (down 13.3 pts)                                -> margin_leak, HIGH
SALT sold on 8 days from 21 Sep to 4 Oct, none since                        -> product_stopped, MEDIUM
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.services import alerts
from tests.test_intelligence_api import make_shop

D = Decimal


@pytest.fixture(autouse=True)
def _no_festival_alerts(monkeypatch):
    """These tests use today's date for the calendar; keep them about the sales rules only."""
    monkeypatch.setattr(alerts, "rule_events", lambda db, ws, today: [])


HEAD = "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status"
SUNDAYS = {date(2026, 8, 30): 10, date(2026, 9, 6): 12, date(2026, 9, 13): 8, date(2026, 9, 20): 10,
           date(2026, 9, 27): 10, date(2026, 10, 4): 9, date(2026, 10, 11): 11, date(2026, 10, 18): 10}  # fmt: skip
SALT_DAYS = [date(2026, 9, d) for d in (20, 21, 22, 24, 26, 28, 30)] + [
    date(2026, 10, 2),
    date(2026, 10, 4),
]


def line(bill, d, sku, name, qty, rate, cost, disc=0):
    return f"{bill},{d:%d/%m/%Y},{sku},{name},Cat,{qty},{rate},{disc},{cost},,,,Store,Paid"


def shop_csv() -> str:
    rows = [HEAD]
    d = date(2026, 8, 30)
    while d <= date(2026, 10, 25):
        qty = SUNDAYS.get(d, 10)
        if d == date(2026, 10, 25):
            qty = 4
        disc = qty * 100 // 10 if d >= date(2026, 10, 19) else 0
        rows.append(line(f"A{d:%m%d}", d, "SKU-A", "Atta", qty, 100, 60, disc))
        d += timedelta(days=1)
    for d in SALT_DAYS:
        rows.append(line(f"S{d:%m%d}", d, "SKU-S", "Salt", 5, 30, 20))
    rows.append(line("O1", date(2026, 9, 10), "SKU-O", "Oil", 5, 150, 100))
    rows.append(line("O2", date(2026, 10, 10), "SKU-O", "Oil", 5, 150, 120))
    return "\n".join(rows) + "\n"


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "al@shop.in", shop_csv())


def url(shop, path=""):
    return f"/api/v1/workspaces/{shop[1]}/alerts{path}"


def by_key(items):
    return {a["key"]: a for a in items}


# ---------------------------------------------------------------- pure statistics


def test_median_and_mad_resist_outliers() -> None:
    xs = [D(v) for v in (800, 1000, 1000, 1000, 1050, 1100, 1150, 1200)]
    m = alerts.median(xs)
    assert m == D(1025)
    assert alerts.mad(xs, m) == D(50)
    r = alerts.robust_change(D(360), xs)
    assert round(float(r["change_pct"]), 1) == -64.9
    assert round(float(r["z"]), 2) == -8.97
    flat = alerts.robust_change(D(500), [D(1000)] * 8)
    assert flat["z"] is None  # MAD of zero: no z-score, only the percentage applies
    assert alerts.median([D(1), D(3), D(2)]) == D(2)


# ---------------------------------------------------------------- rules on the shop


def test_every_rule_fires_with_hand_computed_evidence(client: TestClient, shop) -> None:
    r = client.get(url(shop), params={"as_of": "2026-10-25"}, headers=shop[0]).json()
    a = by_key(r["items"])
    drop = a["sales_drop|2026-10-25"]
    assert drop["severity"] == "high"
    assert round(drop["evidence"]["change_pct"], 1) == -64.9
    assert round(drop["evidence"]["z"], 1) == -9.0
    assert drop["evidence"]["expected"] == 1025
    assert drop["evidence"]["actual"] == 360
    assert "below a usual Sunday" in drop["title"]
    week = a["week_drop|2026-10-25"]
    assert week["severity"] == "medium"
    assert -23.5 < week["evidence"]["change_pct"] < -22.5
    assert week["evidence"]["week"] == 5760
    disc = a["discount_creep"]
    assert disc["severity"] == "high"
    assert round(disc["evidence"]["points"], 1) == 10.0
    leak = a["margin_leak|SKU-O"]
    assert leak["severity"] == "high"
    assert leak["evidence"]["suggested_price"] == 180
    assert leak["link"] == "/app/costs"
    stop = a["product_stopped|SKU-S"]
    assert stop["severity"] == "medium"
    assert stop["evidence"]["selling_days_before"] == 8
    assert "product_stopped|SKU-A" not in a
    assert r["counts"] == {"high": 3, "medium": 2, "info": 1}  # info: data is stale vs today
    assert [x["severity"] for x in r["items"]] == [
        "high",
        "high",
        "high",
        "medium",
        "medium",
        "info",
    ]


def test_no_alerts_on_an_ordinary_day(client: TestClient, shop) -> None:
    """As of 17 Oct (a normal Saturday) nothing is wrong; the later problems have not happened yet."""
    r = client.get(url(shop), params={"as_of": "2026-10-17"}, headers=shop[0]).json()
    rules = {x["rule"] for x in r["items"]}
    assert "sales_drop" not in rules
    assert "discount_creep" not in rules
    assert "week_drop" not in rules


def test_lifecycle_dedupe_resolve_dismiss_reopen(client: TestClient, shop, make_user) -> None:
    h = shop[0]
    first = client.get(url(shop), params={"as_of": "2026-10-25"}, headers=h).json()
    again = client.get(url(shop), params={"as_of": "2026-10-25"}, headers=h).json()
    assert [x["id"] for x in first["items"]] == [x["id"] for x in again["items"]]  # no duplicates

    target = by_key(first["items"])["discount_creep"]
    dismissed = client.post(url(shop, f"/{target['id']}/dismiss"), headers=h).json()
    assert dismissed["status"] == "dismissed"
    open_now = client.get(url(shop), params={"as_of": "2026-10-25"}, headers=h).json()
    assert "discount_creep" not in by_key(open_now["items"])  # stays dismissed while it lasts
    assert open_now["counts"]["high"] == 2
    gone = client.get(
        url(shop), params={"status": "dismissed", "as_of": "2026-10-25"}, headers=h
    ).json()
    assert [x["key"] for x in gone["items"]] == ["discount_creep"]

    back = client.post(url(shop, f"/{target['id']}/reopen"), headers=h).json()
    assert back["status"] == "open"

    # time moves back to a calm day: the problems are no longer true, so they resolve
    calm = client.get(url(shop), params={"status": "open", "as_of": "2026-10-17"}, headers=h).json()
    assert not any(x["key"] in ("sales_drop|2026-10-25", "discount_creep") for x in calm["items"])
    resolved = client.get(
        url(shop), params={"status": "resolved", "as_of": "2026-10-17"}, headers=h
    ).json()
    assert "sales_drop|2026-10-25" in by_key(resolved["items"])

    # and a problem that returns reopens the same alert instead of creating a second one
    client.get(url(shop), params={"as_of": "2026-10-25"}, headers=h)
    all_ = client.get(url(shop), params={"status": "all", "as_of": "2026-10-25"}, headers=h).json()
    assert len([x for x in all_["items"] if x["key"] == "discount_creep"]) == 1
    assert by_key(all_["items"])["discount_creep"]["status"] == "open"


def test_summary_reads_without_recomputing_and_tenancy(client: TestClient, shop, make_user) -> None:
    h = shop[0]
    assert client.get(url(shop, "/summary"), headers=h).json() == {
        "high": 0,
        "medium": 0,
        "info": 0,
    }
    client.get(url(shop), params={"as_of": "2026-10-25"}, headers=h)
    assert client.get(url(shop, "/summary"), headers=h).json()["high"] == 3
    stranger = make_user("s@x.in", "S")
    assert client.get(url(shop), headers=stranger).status_code == 404
    items = client.get(url(shop), params={"as_of": "2026-10-25"}, headers=h).json()["items"]
    assert client.post(url(shop, f"/{items[0]['id']}/dismiss"), headers=stranger).status_code == 404


def test_empty_workspace_has_no_alerts(client: TestClient, make_user) -> None:
    h = make_user("e@x.in", "E")
    ws = client.post("/api/v1/workspaces", json={"name": "Empty"}, headers=h).json()["id"]
    r = client.get(f"/api/v1/workspaces/{ws}/alerts", headers=h).json()
    assert r["items"] == []
    assert r["as_of"] is None


def test_a_high_alert_becomes_the_digests_action(client: TestClient, shop) -> None:
    d = client.get(f"/api/v1/workspaces/{shop[1]}/digests/preview", headers=shop[0]).json()
    assert d["action"]["kind"] == "alert"
    assert (
        "below a usual Sunday" in d["action"]["title"]
    )  # sales_drop outranks margin leak and discounts
    assert d["action"]["link"] == "/app/sales"
    assert "Do this: Sales on Sun 25 Oct" in d["text"]
