# ruff: noqa: E501  (CSV fixture rows are clearer one per line)
"""Customer, product and basket intelligence against small datasets computed by hand.

CUSTOMERS (as of 2026-10-31, all history): one order each unless noted; net = rate, 1 unit
  A  05 Aug 100 · 10 Sep 100 · 28 Oct 200      3 orders  net 400  last 3 days ago
  B  20 Aug 300 · 30 Oct 100                   2 orders  net 400  last 1 day ago
  C  15 Sep 500 (+ a cancelled order on 20 Oct)  1 order net 500  last 46 days ago
  D  25 Oct 50                                 1 order   net 50   last 6 days ago
  E  10 Aug 150 · 25 Aug 150                   2 orders  net 300  last 67 days ago
  F  31 Oct 80                                 1 order   net 80   last 0 days ago
  walk-ins: 15 Oct 200 · 16 Oct 200
Hand-computed R/F/M scores: A 3/5/4 · B 4/4/4 · C 2/2/5 · D 3/2/1 · E 1/4/3 · F 5/2/2
Segments: A Loyal · B Champions · C Hibernating · D New · E At risk · F New
"""

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_ingestion import full_flow

D = Decimal

CUSTOMERS_CSV = """Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status
A1,05/08/2026,SKU1,Item,Cat,1,100,0,60,A,MH,Pune,Store,Paid
A2,10/09/2026,SKU1,Item,Cat,1,100,0,60,A,MH,Pune,Store,Paid
A3,28/10/2026,SKU1,Item,Cat,1,200,0,120,A,MH,Pune,Store,Paid
B1,20/08/2026,SKU1,Item,Cat,1,300,0,180,B,MH,Pune,Store,Paid
B2,30/10/2026,SKU1,Item,Cat,1,100,0,60,B,GJ,Surat,Store,Paid
C1,15/09/2026,SKU1,Item,Cat,1,500,0,300,C,GJ,Surat,Store,Paid
C2,20/10/2026,SKU1,Item,Cat,1,999,0,600,C,GJ,Surat,Store,Cancelled
D1,25/10/2026,SKU1,Item,Cat,1,50,0,30,D,MH,Pune,Store,Paid
E1,10/08/2026,SKU1,Item,Cat,1,150,0,90,E,MH,Pune,Store,Paid
E2,25/08/2026,SKU1,Item,Cat,1,150,0,90,E,MH,Pune,Store,Paid
F1,31/10/2026,SKU1,Item,Cat,1,80,0,48,F,MH,Pune,Store,Paid
W1,15/10/2026,SKU1,Item,Cat,1,200,0,120,,,,Store,Paid
W2,16/10/2026,SKU1,Item,Cat,1,200,0,120,,,,Store,Paid
"""

# Reused from the analytics tests: ATT / GHE / TEA over 24 Sep - 7 Oct.
PRODUCTS_CSV = """Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,Channel,Status
P-1,24/09/2026,ATT,Atta,Staples,10,100,0,80,C1,MH,Store,Paid
P-2,26/09/2026,GHE,Ghee,Dairy,5,200,50,150,C2,MH,Store,Paid
P-3,28/09/2026,ATT,Atta,Staples,5,100,0,80,,,Phone,Paid
C-1,01/10/2026,ATT,Atta,Staples,8,110,0,80,C1,MH,Store,Paid
C-2,01/10/2026,GHE,Ghee,Dairy,4,200,40,150,C3,GJ,Store,Paid
C-3,03/10/2026,ATT,Atta,Staples,2,110,0,80,C2,MH,Phone,Paid
C-3,03/10/2026,TEA,Tea,Beverages,6,50,0,,C2,MH,Phone,Paid
C-4,05/10/2026,GHE,Ghee,Dairy,3,200,0,150,,,Store,Paid
"""

# 8 orders: six with ATT + GHE together, one ATT alone, one TEA alone.
BASKET_ROWS = [
    f"B{i},0{i}/10/2026,{s},{s},Cat,1,100,0,60,,,Store,Paid"
    for i in range(1, 7)
    for s in ("ATT", "GHE")
]
BASKET_ROWS += [
    "B7,07/10/2026,ATT,ATT,Cat,1,100,0,60,,,Store,Paid",
    "B8,08/10/2026,TEA,TEA,Cat,1,100,0,60,,,Store,Paid",
]
BASKET_CSV = (
    "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,Channel,Status\n"
    + "\n".join(BASKET_ROWS)
    + "\n"
)


def make_shop(client: TestClient, make_user, email: str, csv_text: str):
    h = make_user(email, "Owner")
    ws_id = client.post("/api/v1/workspaces", json={"name": "Shop"}, headers=h).json()["id"]
    _, base, summary = full_flow(client, h, ws_id, csv_text.encode(), "data.csv")
    assert summary["rows_invalid"] == 0, summary["sample_errors"]
    job = client.post(f"{base}/import", headers=h).json()
    done = client.get(f"/api/v1/workspaces/{ws_id}/jobs/{job['id']}", headers=h).json()
    assert done["status"] == "succeeded", done
    return h, ws_id


@pytest.fixture
def cust(client, make_user):
    return make_shop(client, make_user, "cust@shop.in", CUSTOMERS_CSV)


@pytest.fixture
def prod(client, make_user):
    return make_shop(client, make_user, "prod@shop.in", PRODUCTS_CSV)


@pytest.fixture
def bask(client, make_user):
    return make_shop(client, make_user, "bask@shop.in", BASKET_CSV)


def get(client, shop, path, **params):
    h, ws_id = shop
    return client.get(f"/api/v1/workspaces/{ws_id}/analytics{path}", params=params, headers=h)


def dec(x):
    return None if x is None else D(x)


# ---------------------------------------------------------------- customers: summary


def test_customer_summary_matches_hand_computed_values(client, cust) -> None:
    r = get(client, cust, "/customers/summary")
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["params"]["as_of"] == "2026-10-31"
    assert s["customers"] == 6
    assert dec(s["net"]) == D("1730.00")  # cancelled and walk-in orders are not customers' sales
    assert s["repeat_customers"] == 3  # A, B, E
    assert dec(s["repeat_rate"]) == D("50.00")
    assert dec(s["revenue_per_customer"]) == D("288.33")
    assert dec(s["avg_orders_per_customer"]) == D("1.7")
    assert dec(s["top_decile_share"]) == D("28.90")  # C alone: 500 / 1730
    assert s["lapsed_regulars"] == 1  # E
    assert s["status_counts"] == {"Active": 4, "Cooling": 0, "Lapsed": 2}
    assert dec(s["walk_in_share"]) == D("16.67")  # 2 of 12 completed orders
    assert any("Only 6 customers" in w for w in s["warnings"])


def test_segments_reconcile_and_match_rules(client, cust) -> None:
    s = get(client, cust, "/customers/summary").json()
    seg = {x["segment"]: x for x in s["segments"]}
    assert {k: v["customers"] for k, v in seg.items()} == {
        "Champions": 1,
        "Loyal": 1,
        "New": 2,
        "Promising": 0,
        "Needs attention": 0,
        "Can't lose": 0,
        "At risk": 1,
        "Hibernating": 1,
    }
    assert sum(x["customers"] for x in s["segments"]) == s["customers"]
    assert sum(dec(x["net"]) for x in s["segments"]) == dec(s["net"])
    assert dec(seg["New"]["net"]) == D("130.00")  # D 50 + F 80
    assert all(x["help"] for x in s["segments"])
    assert sum(sum(row) for row in s["rfm_grid"]) == 6
    assert len(s["rfm_grid"]) == 5
    assert all(len(row) == 5 for row in s["rfm_grid"])


def test_customer_list_scores_each_customer(client, cust) -> None:
    items = get(client, cust, "/customers/list", limit=50).json()["items"]
    by = {c["key"]: c for c in items}
    expected = {
        "A": (3, 5, 4, "Loyal", "Active", 3, 3),
        "B": (4, 4, 4, "Champions", "Active", 2, 1),
        "C": (2, 2, 5, "Hibernating", "Lapsed", 1, 46),
        "D": (3, 2, 1, "New", "Active", 1, 6),
        "E": (1, 4, 3, "At risk", "Lapsed", 2, 67),
        "F": (5, 2, 2, "New", "Active", 1, 0),
    }
    for key, (r, f, m, seg, status, orders, days) in expected.items():
        c = by[key]
        assert (c["r"], c["f"], c["m"]) == (r, f, m), key
        assert (c["segment"], c["status"], c["orders"], c["recency_days"]) == (
            seg,
            status,
            orders,
            days,
        ), key
    assert dec(by["A"]["net"]) == D("400.00")
    assert dec(by["A"]["aov"]) == D("133.33")
    assert by["C"]["last_order"] == "2026-09-15"  # the cancelled order on 20 Oct does not count
    assert by["A"]["first_order"] == "2026-08-05"


def test_customer_list_filters_sorting_and_paging(client, cust) -> None:
    body = get(client, cust, "/customers/list", segment="New").json()
    assert body["total"] == 2
    assert {c["key"] for c in body["items"]} == {"D", "F"}
    body = get(client, cust, "/customers/list", status="Lapsed", sort="recency").json()
    assert [c["key"] for c in body["items"]] == ["E", "C"]  # longest quiet first
    body = get(client, cust, "/customers/list", sort="net", limit=2).json()
    assert body["items"][0]["key"] == "C"  # biggest spender first
    assert body["total"] == 6
    assert len(get(client, cust, "/customers/list", limit=2, offset=4).json()["items"]) == 2
    # city comes from each customer's first order: A, B, D, E, F are in Pune; C is in Surat
    assert get(client, cust, "/customers/list", search="pune").json()["total"] == 5
    assert get(client, cust, "/customers/list", search="surat").json()["total"] == 1
    assert get(client, cust, "/customers/list", segment="Nonsense").status_code == 422


def test_as_of_and_window_parameters(client, cust) -> None:
    # Looking back only 30 days from 31 Oct: C (15 Sep) and E (Aug) drop out.
    s = get(client, cust, "/customers/summary", lookback_days=30).json()
    assert s["customers"] == 4  # A, B, D, F
    # Earlier as-of date: only customers who had bought by then
    s = get(client, cust, "/customers/summary", as_of="2026-09-30").json()
    assert s["customers"] == 4  # A (Aug, Sep), B (Aug), C (Sep), E (Aug)
    assert s["params"]["as_of"] == "2026-09-30"
    r = get(client, cust, "/customers/summary", active_days=40, lapse_days=30)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_params"


# ---------------------------------------------------------------- cohorts


def test_cohort_retention_matrix(client, cust) -> None:
    body = get(client, cust, "/customers/cohorts").json()
    rows = {c["cohort"]: c for c in body["cohorts"]}
    assert set(rows) == {"2026-08", "2026-09", "2026-10"}
    aug = rows["2026-08"]
    assert aug["size"] == 3  # A, B, E first bought in August
    assert aug["counts"] == [3, 1, 2]  # Sep: only A · Oct: A and B
    assert [dec(x) for x in aug["retention"]] == [D("100.00"), D("33.33"), D("66.67")]
    assert rows["2026-09"]["counts"] == [1, 0]  # C never returned
    assert rows["2026-10"]["counts"] == [2]  # D and F are brand new
    assert body["months"] == 3
    assert body["warnings"] == []


def test_cohorts_warn_with_little_history(client, bask) -> None:
    body = get(client, bask, "/customers/cohorts").json()
    assert body["cohorts"] == []
    assert body["warnings"]


# ---------------------------------------------------------------- exports


def test_customer_csv_export_matches_the_list(client, cust) -> None:
    r = get(client, cust, "/customers/export.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("customer,segment,status")
    assert len(lines) == 7  # header + 6 customers
    r = get(client, cust, "/customers/export.csv", segment="New")
    assert len(r.text.strip().splitlines()) == 3
    assert "customers_new.csv" in r.headers["content-disposition"]
    r = get(client, cust, "/customers/export.csv", segment="Can't lose")
    assert "customers_cant_lose.csv" in r.headers["content-disposition"]


# ---------------------------------------------------------------- products

PERIOD = {"from": "2026-10-01", "to": "2026-10-07"}


def test_product_margin_abc_and_quadrants(client, prod) -> None:
    r = get(client, prod, "/products", **PERIOD)
    assert r.status_code == 200, r.text
    body = r.json()
    items = {i["key"]: i for i in body["items"]}
    assert [i["key"] for i in body["items"]] == ["GHE", "ATT", "TEA"]  # by net sales
    assert dec(body["overall_margin_pct"]) == D("24.80")  # (2460 - 1850) / 2460
    assert dec(body["overall_discount_rate"]) == D("1.43")  # 40 / 2800

    assert dec(items["GHE"]["net"]) == D("1360.00")
    assert dec(items["GHE"]["margin_pct"]) == D("22.79")  # (1360 - 1050) / 1360
    assert dec(items["ATT"]["margin_pct"]) == D("27.27")  # (1100 - 800) / 1100
    assert items["TEA"]["margin_pct"] is None  # no cost recorded
    assert "no_cost" in items["TEA"]["flags"]

    assert [items[k]["abc"] for k in ("GHE", "ATT", "TEA")] == ["A", "A", "B"]
    assert dec(items["GHE"]["share"]) == D("49.28")
    assert items["ATT"]["quadrant"] == "Star"  # popular and above the overall margin
    assert items["GHE"]["quadrant"] == "Workhorse"  # popular, margin below overall
    assert items["TEA"]["quadrant"] == "Unknown"
    q = {x["quadrant"]: x["products"] for x in body["portfolio"]["quadrants"]}
    assert q["Star"] == 1
    assert q["Workhorse"] == 1
    assert body["portfolio"]["abc"] == {"A": 2, "B": 1, "C": 0}


def test_product_change_flags_and_categories(client, prod) -> None:
    body = get(client, prod, "/products", **PERIOD).json()
    items = {i["key"]: i for i in body["items"]}
    assert dec(items["ATT"]["previous_net"]) == D("1500.00")
    assert dec(items["ATT"]["change_pct"]) == D("-26.67")
    assert "declining" in items["ATT"]["flags"]
    assert dec(items["GHE"]["change_pct"]) == D("43.16")  # 950 -> 1360
    assert "rising" in items["GHE"]["flags"]
    assert items["TEA"]["change_pct"] is None  # new this period: no percentage
    cats = {c["category"]: c for c in body["categories"]}
    assert dec(cats["Staples"]["net"]) == D("1100.00")
    assert dec(cats["Dairy"]["margin_pct"]) == D("22.79")
    assert cats["Beverages"]["margin_pct"] is None
    assert sum(dec(c["net"]) for c in body["categories"]) == D(
        "2760.00"
    )  # reconciles with the KPIs


def test_products_without_comparison_and_with_filters(client, prod) -> None:
    body = get(client, prod, "/products", compare="none", **PERIOD).json()
    assert all(i["previous_net"] is None for i in body["items"])
    body = get(client, prod, "/products", category="Dairy", **PERIOD).json()
    assert [i["key"] for i in body["items"]] == ["GHE"]
    body = get(client, prod, "/products", region="GJ", **PERIOD).json()
    assert [i["key"] for i in body["items"]] == ["GHE"]  # the only GJ order


def test_product_csv_export(client, prod) -> None:
    r = get(client, prod, "/products/export.csv", **PERIOD)
    assert r.status_code == 200
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("sku,product,category")
    assert len(lines) == 4
    assert lines[1].startswith("GHE,Ghee,Dairy")


# ---------------------------------------------------------------- basket


def test_basket_pair_statistics(client, bask) -> None:
    r = get(client, bask, "/basket", **{"from": "2026-10-01", "to": "2026-10-08"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["orders"] == 8
    assert body["multi_item_orders"] == 6
    assert dec(body["multi_item_share"]) == D("75.00")
    assert dec(body["avg_items_per_order"]) == D("1.75")
    assert len(body["pairs"]) == 1
    p = body["pairs"][0]
    assert {p["a"], p["b"]} == {"ATT", "GHE"}
    assert p["orders"] == 6
    assert dec(p["support"]) == D("75.00")
    assert dec(p["lift"]) == D("1.14")  # 6 * 8 / (7 * 6)
    att_first = p["a"] == "ATT"
    assert dec(p["confidence_a_to_b"]) == (D("85.71") if att_first else D("100.00"))
    assert "not that one product causes" in body["note"]


def test_basket_minimum_orders(client, bask) -> None:
    body = get(
        client, bask, "/basket", min_orders=7, **{"from": "2026-10-01", "to": "2026-10-08"}
    ).json()
    assert body["pairs"] == []
    assert get(client, bask, "/basket", min_orders=1).status_code == 422


# ---------------------------------------------------------------- tenancy and empty workspaces

PATHS = [
    "/customers/summary",
    "/customers/list",
    "/customers/cohorts",
    "/customers/export.csv",
    "/products",
    "/products/export.csv",
    "/basket",
]


def test_outsiders_get_404_and_anonymous_gets_401(client, cust, make_user) -> None:
    _, ws_id = cust
    outsider = make_user("out@else.in")
    for path in PATHS:
        r = client.get(f"/api/v1/workspaces/{ws_id}/analytics{path}", headers=outsider)
        assert r.status_code == 404, path
        assert client.get(f"/api/v1/workspaces/{ws_id}/analytics{path}").status_code == 401, path


def test_viewer_can_read_and_tenants_do_not_leak(client, cust, make_user) -> None:
    h, ws_id = cust
    viewer = make_user("viewer@cust.in")
    client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "viewer@cust.in", "role": "viewer"},
        headers=h,
    )
    r = client.get(f"/api/v1/workspaces/{ws_id}/analytics/customers/summary", headers=viewer)
    assert r.status_code == 200
    assert r.json()["customers"] == 6
    other = make_user("other@owner.in")
    other_ws = client.post("/api/v1/workspaces", json={"name": "Other"}, headers=other).json()["id"]
    body = client.get(
        f"/api/v1/workspaces/{other_ws}/analytics/customers/summary", headers=other
    ).json()
    assert body["customers"] == 0


def test_empty_workspace_returns_empty_results(client, make_user) -> None:
    h = make_user("empty@shop.in")
    ws_id = client.post("/api/v1/workspaces", json={"name": "Empty"}, headers=h).json()["id"]
    base = f"/api/v1/workspaces/{ws_id}/analytics"
    s = client.get(f"{base}/customers/summary", headers=h).json()
    assert s["customers"] == 0
    assert s["repeat_rate"] is None
    assert any("nothing to segment" in w for w in s["warnings"])
    assert client.get(f"{base}/customers/list", headers=h).json()["items"] == []
    assert client.get(f"{base}/customers/cohorts", headers=h).json()["cohorts"] == []
    p = client.get(f"{base}/products", headers=h).json()
    assert p["items"] == []
    assert "No products sold in this period." in p["warnings"]
    assert client.get(f"{base}/basket", headers=h).json()["pairs"] == []
    assert client.get(f"{base}/customers/export.csv", headers=h).text.strip().count("\n") == 0


def test_segment_literals_match_the_rules() -> None:
    from typing import get_args

    from app.api.v1.endpoints.intelligence import SegmentName, StatusName
    from app.services.analytics.customers import SEGMENTS, STATUSES

    assert list(get_args(SegmentName)) == SEGMENTS
    assert list(get_args(StatusName)) == STATUSES


# ---------------------------------------------------------------- realistic data

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample" / "vyapar_demo_sales.csv"


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample data not generated")
def test_intelligence_reconciles_on_the_8k_row_sample(client, make_user) -> None:
    h, ws_id = make_shop(client, make_user, "big@intel.in", SAMPLE.read_text())
    base = f"/api/v1/workspaces/{ws_id}/analytics"

    s = client.get(f"{base}/customers/summary", headers=h).json()
    assert s["customers"] > 100
    assert sum(x["customers"] for x in s["segments"]) == s["customers"]
    assert sum(dec(x["net"]) for x in s["segments"]) == dec(s["net"])
    assert sum(s["status_counts"].values()) == s["customers"]
    assert sum(sum(row) for row in s["rfm_grid"]) == s["customers"]
    listing = client.get(f"{base}/customers/list", params={"limit": 200}, headers=h).json()
    assert listing["total"] == s["customers"]
    assert all(1 <= c["r"] <= 5 and 1 <= c["f"] <= 5 and 1 <= c["m"] <= 5 for c in listing["items"])

    coh = client.get(f"{base}/customers/cohorts", headers=h).json()
    assert [c["cohort"] for c in coh["cohorts"]] == ["2026-08", "2026-09", "2026-10"]
    assert (
        sum(c["size"] for c in coh["cohorts"]) == s["customers"]
    )  # every customer is in one cohort
    assert all(dec(c["retention"][0]) == D("100.00") for c in coh["cohorts"])

    period = {"from": "2026-08-01", "to": "2026-10-31"}
    p = client.get(f"{base}/products", params={**period, "compare": "none"}, headers=h).json()
    overview = client.get(
        f"{base}/overview", params={**period, "compare": "none"}, headers=h
    ).json()
    net = dec(next(k for k in overview["headline"] if k["key"] == "net_sales")["value"])
    assert sum(dec(i["net"]) for i in p["items"]) == net
    assert sum(dec(c["net"]) for c in p["categories"]) == net
    assert abs(sum(dec(i["share"]) for i in p["items"]) - 100) <= D("0.1")
    assert dec(p["items"][-1]["cumulative_share"]) == D("100.00")
    assert sum(x["products"] for x in p["portfolio"]["quadrants"]) == len(p["items"])
    assert sum(p["portfolio"]["abc"].values()) == len(p["items"])

    b = client.get(f"{base}/basket", params={**period, "min_orders": 20}, headers=h).json()
    assert b["orders"] > 1000
    assert all(x["lift"] and dec(x["support"]) <= 100 for x in b["pairs"])
