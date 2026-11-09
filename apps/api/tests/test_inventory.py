# ruff: noqa: E501
"""Inventory planning checked against hand-computed numbers.

Pure rules (lead 3 days, review 7, so the window is 10 days; p50 = 10 a day, p90 = 14 a day,
service 0.5 means planned demand 10 + 0.5 x 4 = 12 a day, 120 over the window):
  on hand 25  -> cover 2.5 days  < lead 3   URGENT   order 120 - 25 = 95
  on hand 80  -> cover 8.0 days <= 10       REORDER  order 120 - 80 = 40 (48 with packs of 12)
  on hand 150 -> cover 15 days              OK
  on hand 1000 -> cover far past 45 days    OVERSTOCK

Shop (forecast built from 84 days; weekly pattern for SKU-A, 5 a day for SKU-B, rare SKU-C):
  SKU-A snapshot 100 on 20 Oct; sold 21-25 Oct = 8 + 9 + 10 + 16 + 14 = 57  -> 43 on hand today
  SKU-B 10 on hand at 5 a day -> about 2 days: urgent
  SKU-C 500 on hand at cost 120 -> 60,000 tied up, hugely overstocked
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.services import inventory
from tests.test_forecast_api import run_forecast, shop_csv
from tests.test_intelligence_api import make_shop

D = Decimal
Z = Decimal(0)


def flat(v, n=14):
    return [D(v)] * n


def plan(on_hand, **kw):
    args = {"lead": 3, "review": 7, "pack": D(1), "service": D("0.5"), "sold_last_30": D(100)}
    return inventory.plan(D(on_hand), flat(10), flat(14), **{**args, **kw})


# ---------------------------------------------------------------- pure planning


def test_cover_walks_the_daily_forecast_then_a_flat_rate() -> None:
    assert inventory.cover(D(35), flat(10), D(10)) == D("3.5")
    assert inventory.cover(D(0), flat(10), D(10)) == 0
    assert inventory.cover(D(140), flat(10), D(10)) == D(14)  # exactly the forecast
    assert inventory.cover(D(200), flat(10), D(10)) == D(
        20
    )  # 140 in the forecast, 60 more at 10 a day
    assert inventory.cover(D(5), flat(0), D(0)) is None  # no demand: never runs out


def test_urgent_reorder_ok_overstock_thresholds_and_quantities() -> None:
    urgent = plan(25)
    assert (urgent.status, urgent.order_qty) == ("urgent", D(95))
    assert urgent.cover_days == D("2.5")
    reorder = plan(80)
    assert (reorder.status, reorder.order_qty) == ("reorder", D(40))
    assert plan(80, pack=D(12)).order_qty == D(48)  # rounded up to whole packs
    ok = plan(150)
    assert (ok.status, ok.order_qty) == ("ok", Z)
    big = plan(1000)
    assert big.status == "overstock"
    assert "60+" in big.reason
    assert plan(30).status == "reorder"  # exactly 3 days of cover is not below the lead time
    assert plan(30, lead=2).status == "reorder"
    assert plan(100).status == "reorder"  # 10 days of cover is the edge of the window
    assert plan(101).status == "ok"


def test_service_level_raises_the_order_quantity() -> None:
    lean, balanced, safe = (plan(25, service=D(s)).order_qty for s in ("0", "0.5", "1"))
    assert (lean, balanced, safe) == (D(75), D(95), D(115))  # 100/120/140 over the window, less 25


def test_dead_stock_and_no_demand_are_not_false_alarms() -> None:
    dead = inventory.plan(
        D(40), flat(0), flat(0), lead=3, review=7, pack=D(1), service=D("0.5"), sold_last_30=Z
    )
    assert dead.status == "dead"
    assert (
        inventory.plan(
            Z, flat(0), flat(0), lead=3, review=7, pack=D(1), service=D("0.5"), sold_last_30=D(5)
        ).status
        == "ok"
    )


# ---------------------------------------------------------------- file parsing


def test_parser_understands_common_headers_and_reports_bad_rows() -> None:
    csv_text = "Item Code,Closing Stock,Stock Date,Lead Time,Pack Size\nA,12,25/10/2026,5,6\nB,-3,25/10/2026,,\nC,abc,,,\nD,4,31-12-2026,,\n,7,,,\nE,9,2026-10-24,,\nE,11,2026-10-24,,\n"
    rows, rejects = inventory.parse_stock_file(
        csv_text.encode(), __import__("datetime").date(2026, 10, 25)
    )
    by = {r["sku"]: r for r in rows}
    assert by["A"]["on_hand"] == 12
    assert by["A"]["lead"] == 5
    assert by["A"]["pack"] == 6
    assert by["E"]["on_hand"] == 11  # the last row for a product and date wins
    assert len(rows) == 2
    reasons = " | ".join(r["reason"] for r in rejects)
    assert "zero or more" in reasons
    assert "not understood" in reasons
    assert "No product code" in reasons
    assert len(rejects) == 4


def test_parser_rejects_files_without_the_needed_columns() -> None:
    for bad in (b"", b"Name,Colour\nx,y\n", b"SKU,Colour\nx,y\n"):
        with pytest.raises(inventory.BadFileError):
            inventory.parse_stock_file(bad, __import__("datetime").date(2026, 10, 25))


# ---------------------------------------------------------------- API


@pytest.fixture
def shop(client: TestClient, make_user):
    s = make_shop(client, make_user, "inv@shop.in", shop_csv(84))
    run_forecast(client, s)
    return s


def url(shop, path):
    return f"/api/v1/workspaces/{shop[1]}/inventory{path}"


def upload(client, shop, text: str, as_of: str = "2026-10-25"):
    return client.post(
        url(shop, "/import"),
        files={"file": ("stock.csv", text.encode(), "text/csv")},
        data={"as_of": as_of},
        headers=shop[0],
    )


STOCK = "SKU,Stock,Date\nSKU-A,100,2026-10-20\nSKU-B,10,2026-10-25\nSKU-C,500,2026-10-25\n"


def test_overview_applies_sales_since_the_snapshot_and_flags_each_product(
    client: TestClient, shop
) -> None:
    r = upload(client, shop, STOCK)
    assert r.status_code == 200
    assert r.json()["imported"] == 3
    ov = client.get(url(shop, "/overview"), headers=shop[0]).json()
    by = {i["sku"]: i for i in ov["items"]}
    a = by["SKU-A"]
    assert D(a["snapshot_on_hand"]) == 100
    assert D(a["sold_since"]) == 57  # 8 + 9 + 10 + 16 + 14
    assert D(a["on_hand"]) == 43
    assert 3 <= float(a["cover_days"]) <= 6
    assert a["status"] in ("reorder", "urgent")
    assert D(a["order_qty"]) > 0
    b = by["SKU-B"]
    assert b["status"] == "urgent"
    assert float(b["cover_days"]) < 3
    assert b["run_out_date"] is not None
    c = by["SKU-C"]
    assert c["status"] == "overstock"
    assert D(c["cash_tied"]) == D("60000.00")  # 500 x cost 120
    assert D(c["order_qty"]) == 0
    s = ov["summary"]
    assert s["tracked"] == 3
    assert s["urgent"] >= 1
    assert D(s["cash_tied"]) >= D("60000.00")
    assert D(s["excess_cash"]) > 0
    assert ov["items"][0]["status"] == "urgent"  # urgent items first
    assert ov["has_forecast"] is True


def test_unmatched_and_rejected_rows_are_reported(client: TestClient, shop) -> None:
    text = "SKU,Stock\nSKU-A,20\nNOPE,5\nSKU-B,-1\n"
    r = upload(client, shop, text).json()
    assert r["imported"] == 1
    assert r["unmatched_skus"] == ["NOPE"]
    assert r["rejected_count"] == 1
    assert upload(client, shop, "Colour,Size\nred,L\n").status_code == 422


def test_lead_time_and_pack_size_change_the_advice(client: TestClient, shop) -> None:
    upload(client, shop, "SKU,Stock,Lead Time,Pack Size\nSKU-B,10,7,12\n")
    b = {i["sku"]: i for i in client.get(url(shop, "/overview"), headers=shop[0]).json()["items"]}[
        "SKU-B"
    ]
    assert b["lead_time_days"] == 7
    assert D(b["pack_size"]) == 12
    assert D(b["order_qty"]) % 12 == 0  # whole packs
    assert D(b["order_qty"]) >= 12
    h = shop[0]
    assert (
        client.put(url(shop, "/items/SKU-B"), json={"lead_time_days": 2}, headers=h).status_code
        == 204
    )
    b2 = {i["sku"]: i for i in client.get(url(shop, "/overview"), headers=h).json()["items"]}[
        "SKU-B"
    ]
    assert b2["lead_time_days"] == 2
    assert (
        client.put(url(shop, "/items/SKU-B"), json={"lead_time_days": 100}, headers=h).status_code
        == 422
    )
    assert (
        client.put(url(shop, "/items/NOPE"), json={"lead_time_days": 2}, headers=h).status_code
        == 404
    )


def test_setting_stock_by_hand_and_the_cautious_service_level(client: TestClient, shop) -> None:
    h = shop[0]
    client.put(url(shop, "/items/SKU-A"), json={"on_hand": 30, "as_of": "2026-10-25"}, headers=h)
    lean = {
        i["sku"]: i
        for i in client.get(url(shop, "/overview"), params={"service": 0}, headers=h).json()[
            "items"
        ]
    }["SKU-A"]
    safe = {
        i["sku"]: i
        for i in client.get(url(shop, "/overview"), params={"service": 1}, headers=h).json()[
            "items"
        ]
    }["SKU-A"]
    assert D(safe["order_qty"]) > D(lean["order_qty"])  # a cautious plan orders more
    assert client.get(url(shop, "/overview"), params={"service": 2}, headers=h).status_code == 422


def test_template_and_order_list_exports(client: TestClient, shop, make_user) -> None:
    h = shop[0]
    t = client.get(url(shop, "/template.csv"), headers=h)
    assert t.status_code == 200
    assert t.text.splitlines()[0].startswith("SKU,Product,Stock")
    assert len(t.text.strip().splitlines()) == 4  # header + three products
    upload(client, shop, STOCK)
    o = client.get(url(shop, "/order-list.csv"), headers=h)
    lines = o.text.strip().splitlines()
    assert lines[0].startswith("sku,product,status")
    assert any(ln.startswith("SKU-B") for ln in lines[1:])
    assert not any(ln.startswith("SKU-C") for ln in lines[1:])  # overstocked: nothing to order
    logs = client.get(f"/api/v1/workspaces/{shop[1]}/audit-logs", headers=h).json()
    assert any(x["action"] == "inventory.order_list_exported" for x in logs["items"])
    stranger = make_user("s@x.in", "S")
    assert client.get(url(shop, "/overview"), headers=stranger).status_code == 404
    assert upload(client, (stranger, shop[1]), STOCK).status_code == 404


def test_without_a_forecast_the_recent_rate_is_used(client: TestClient, make_user) -> None:
    s = make_shop(client, make_user, "nofc@shop.in", shop_csv(84))
    upload(client, s, "SKU,Stock\nSKU-B,10\n")
    ov = client.get(url(s, "/overview"), headers=s[0]).json()
    assert ov["has_forecast"] is False
    b = ov["items"][0]
    assert b["forecast_based"] is False
    assert b["status"] == "urgent"  # 10 units at about 5 a day


def test_stockout_risk_becomes_an_alert_and_the_digests_action(client: TestClient, shop) -> None:
    upload(client, shop, STOCK)
    a = client.get(f"/api/v1/workspaces/{shop[1]}/alerts", headers=shop[0]).json()
    keys = {x["key"]: x for x in a["items"]}
    risk = keys["stockout_risk|SKU-B"]
    assert risk["severity"] == "high"
    assert "will run out" in risk["title"]
    assert risk["link"] == "/app/inventory"
    assert risk["evidence"]["order_qty"] > 0
    d = client.get(f"/api/v1/workspaces/{shop[1]}/digests/preview", headers=shop[0]).json()
    assert d["action"]["kind"] == "alert"
    assert "run out" in d["action"]["title"]


def test_dead_stock_alert_names_the_cash_tied_up(client: TestClient, make_user) -> None:
    s = make_shop(
        client,
        make_user,
        "dead@shop.in",
        shop_csv(84) + "B0101,01/08/2026,SKU-D,Old stock,Cat,1,100,0,40,,,,Store,Paid\n",
    )
    run_forecast(client, s)
    upload(client, s, "SKU,Stock\nSKU-D,50\n")
    a = {
        x["key"]: x
        for x in client.get(f"/api/v1/workspaces/{s[1]}/alerts", headers=s[0]).json()["items"]
    }
    dead = a["dead_stock"]
    assert dead["severity"] == "info"
    assert dead["evidence"]["cash"] == 2000  # 50 units at cost 40
    assert "₹2,000" in dead["title"]
