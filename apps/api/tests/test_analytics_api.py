"""Analytics API against a tiny dataset whose every answer was computed by hand.

Previous period (24-30 Sep)               Current period (1-7 Oct)
 P-1  ATT 10 x 100          = 1000          C-1  ATT 8 x 110              = 880
 P-2  GHE  5 x 200 - 50     =  950          C-2  GHE 4 x 200 - 40         = 760
 P-3  ATT  5 x 100 (walk-in)=  500          C-3  ATT 2 x 110 + TEA 6 x 50 = 520  (TEA has no cost)
 P-4  cancelled (excluded)                  C-4  GHE 3 x 200 (walk-in)    = 600
                                            C-5  returned (excluded)
 net 2450 · 3 orders · cost 1950            net 2760 · 4 orders · cost 1850 (on 2460 of net)
"""

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_ingestion import full_flow

D = Decimal

# ruff: noqa: E501  (CSV fixture rows are clearer one per line)
CSV = """Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,Channel,Status
P-1,24/09/2026,ATT,Atta,Staples,10,100,0,80,C1,MH,Store,Paid
P-2,26/09/2026,GHE,Ghee,Dairy,5,200,50,150,C2,MH,Store,Paid
P-3,28/09/2026,ATT,Atta,Staples,5,100,0,80,,,Phone,Paid
P-4,29/09/2026,ATT,Atta,Staples,3,100,0,80,C1,MH,Store,Cancelled
C-1,01/10/2026,ATT,Atta,Staples,8,110,0,80,C1,MH,Store,Paid
C-2,01/10/2026,GHE,Ghee,Dairy,4,200,40,150,C3,GJ,Store,Paid
C-3,03/10/2026,ATT,Atta,Staples,2,110,0,80,C2,MH,Phone,Paid
C-3,03/10/2026,TEA,Tea,Beverages,6,50,0,,C2,MH,Phone,Paid
C-4,05/10/2026,GHE,Ghee,Dairy,3,200,0,150,,,Store,Paid
C-5,06/10/2026,ATT,Atta,Staples,1,110,0,80,C1,MH,Store,Returned
"""

PERIOD = {"from": "2026-10-01", "to": "2026-10-07"}


@pytest.fixture
def shop(client: TestClient, make_user):
    h = make_user("owner@analytics.in", "Owner")
    ws_id = client.post("/api/v1/workspaces", json={"name": "Analytics Shop"}, headers=h).json()[
        "id"
    ]
    _, base, summary = full_flow(client, h, ws_id, CSV.encode(), "analytics.csv")
    assert summary["rows_invalid"] == 0
    job = client.post(f"{base}/import", headers=h).json()
    assert (
        client.get(f"/api/v1/workspaces/{ws_id}/jobs/{job['id']}", headers=h).json()["status"]
        == "succeeded"
    )
    return h, ws_id


def get(client, shop, path, **params):
    h, ws_id = shop
    r = client.get(f"/api/v1/workspaces/{ws_id}{path}", params=params, headers=h)
    return r


def kpis(body):
    return {k["key"]: k for k in [*body["headline"], *body["secondary"]]}


def dec(x):
    return None if x is None else D(x)


# ---------------------------------------------------------------- registry and options


def test_registry_lists_every_metric_with_versions(client, shop) -> None:
    body = get(client, shop, "/metrics").json()
    keys = {m["key"] for m in body["metrics"]}
    assert {"net_sales", "gross_profit", "aov", "gross_margin", "cost_coverage"} <= keys
    assert body["registry_version"] == 2
    assert all(m["version"] >= 1 and m["definition"] for m in body["metrics"])
    assert any("GST" in a for a in body["assumptions"])


def test_filter_options_and_default_period(client, shop) -> None:
    body = get(client, shop, "/analytics/filters").json()
    assert body["categories"] == ["Beverages", "Dairy", "Staples"]
    assert body["channels"] == ["Phone", "Store"]
    assert body["regions"] == ["GJ", "MH"]
    assert body["last_order_date"] == "2026-10-05"  # the returned order on the 6th is not eligible
    assert body["default_to"] == "2026-10-05"
    assert body["default_from"] == "2026-09-06"  # 30 days ending at the latest order


# ---------------------------------------------------------------- KPIs


def test_kpis_match_hand_computed_values(client, shop) -> None:
    r = get(client, shop, "/analytics/overview", **PERIOD)
    assert r.status_code == 200, r.text
    k = kpis(r.json())

    assert dec(k["net_sales"]["value"]) == D("2760.00")
    assert dec(k["net_sales"]["previous"]) == D("2450.00")
    assert dec(k["net_sales"]["change"]) == D("310.00")
    assert dec(k["net_sales"]["change_pct"]) == D("12.65")

    assert dec(k["orders"]["value"]) == 4
    assert dec(k["orders"]["previous"]) == 3
    assert dec(k["aov"]["value"]) == D("690.00")
    assert dec(k["aov"]["previous"]) == D("816.67")
    assert dec(k["units"]["value"]) == 23
    assert dec(k["units_per_order"]["value"]) == D("5.75")

    assert dec(k["discount_rate"]["value"]) == D("1.43")  # 40 / 2800
    assert dec(k["discount_rate"]["previous"]) == D("2.00")  # 50 / 2500
    assert k["discount_rate"]["change_pct"] is None  # percent metrics change in points
    assert dec(k["discount_rate"]["change"]) == D("-0.57")


def test_profit_margin_and_cost_coverage_use_only_lines_with_a_cost(client, shop) -> None:
    body = get(client, shop, "/analytics/overview", **PERIOD).json()
    k = kpis(body)
    assert dec(k["gross_profit"]["value"]) == D("610.00")  # 2460 - 1850
    assert dec(k["gross_profit"]["previous"]) == D("500.00")  # 2450 - 1950
    assert dec(k["gross_margin"]["value"]) == D("24.80")  # 610 / 2460
    assert dec(k["gross_margin"]["previous"]) == D("20.41")  # 500 / 2450
    # TEA (300 of 2760) has no cost
    assert dec(body["meta"]["coverage"]["cost_coverage_pct"]) == D("89.13")


def test_customer_metrics(client, shop) -> None:
    k = kpis(get(client, shop, "/analytics/overview", **PERIOD).json())
    assert dec(k["active_customers"]["value"]) == 3  # C1, C3, C2
    assert dec(k["active_customers"]["previous"]) == 2
    secondary = {
        m["key"] for m in get(client, shop, "/analytics/overview", **PERIOD).json()["secondary"]
    }
    assert "active_customers" in secondary


def test_coverage_and_exclusions_are_reported(client, shop) -> None:
    body = get(client, shop, "/analytics/overview", **PERIOD).json()
    cov = body["meta"]["coverage"]
    assert cov["excluded_orders_by_status"] == {"returned": 1}
    assert cov["days_in_period"] == 7
    assert cov["days_with_data"] == 3
    assert cov["compare_days_with_data"] == 3
    assert dec(cov["anonymous_order_share"]) == D("25.00")
    assert any("not counted" in w and "returned" in w for w in body["warnings"])
    assert any("Only 89.1% of net sales has a cost" in w for w in body["warnings"])
    assert body["meta"]["metric_versions"]["net_sales"] == 1
    assert body["meta"]["compare"]["date_from"] == "2026-09-24"
    assert body["meta"]["compare"]["date_to"] == "2026-09-30"
    assert body["meta"]["currency"] == "INR"


# ---------------------------------------------------------------- trend and mixes


def test_trend_is_gap_filled_and_aligned_with_the_comparison(client, shop) -> None:
    trend = get(client, shop, "/analytics/overview", **PERIOD).json()["trend"]
    assert len(trend) == 7
    by_start = {p["start"]: p for p in trend}
    assert dec(by_start["2026-10-01"]["net"]) == D("1640.00")
    assert dec(by_start["2026-10-02"]["net"]) == D("0.00")  # empty day is present, not skipped
    assert dec(by_start["2026-10-03"]["net"]) == D("520.00")
    assert dec(by_start["2026-10-05"]["net"]) == D("600.00")
    assert sum(dec(p["net"]) for p in trend) == D("2760.00")  # the trend reconciles to the KPI
    # comparison overlay: same position in the previous period
    assert dec(trend[0]["previous_net"]) == D("1000.00")  # 24 Sep
    assert dec(trend[2]["previous_net"]) == D("950.00")  # 26 Sep
    assert dec(trend[4]["previous_net"]) == D("500.00")  # 28 Sep


def test_breakdowns_by_category_channel_and_region(client, shop) -> None:
    body = get(client, shop, "/analytics/overview", **PERIOD).json()
    cats = {r["key"]: r for r in body["category_mix"]}
    assert dec(cats["Dairy"]["net"]) == D("1360.00")
    assert dec(cats["Staples"]["net"]) == D("1100.00")
    assert dec(cats["Beverages"]["net"]) == D("300.00")
    assert dec(cats["Staples"]["delta"]) == D("-400.00")  # 1500 -> 1100
    assert dec(cats["Dairy"]["delta"]) == D("410.00")  # 950 -> 1360
    assert sum(dec(r["net"]) for r in body["category_mix"]) == D("2760.00")
    assert sum(dec(r["delta"]) for r in body["category_mix"]) == D("310.00")

    channels = {r["key"]: dec(r["net"]) for r in body["channel_mix"]}
    assert channels == {"Store": D("2240.00"), "Phone": D("520.00")}
    regions = {r["key"]: dec(r["net"]) for r in body["region_mix"]}
    assert regions == {"MH": D("1400.00"), "GJ": D("760.00"), "Unspecified": D("600.00")}


def test_top_and_bottom_products_with_change(client, shop) -> None:
    body = get(client, shop, "/analytics/overview", **PERIOD).json()
    top = [(p["sku"], dec(p["net"])) for p in body["top_products"]]
    assert top == [("GHE", D("1360.00")), ("ATT", D("1100.00")), ("TEA", D("300.00"))]
    att = next(p for p in body["top_products"] if p["sku"] == "ATT")
    assert dec(att["previous_net"]) == D("1500.00")
    assert dec(att["delta"]) == D("-400.00")
    assert body["bottom_products"][0]["sku"] == "TEA"
    weekday = {w["label"]: w for w in body["weekday"]}
    assert len(weekday) == 7
    assert dec(weekday["Thu"]["avg_net"]) == D("1640.00")  # 1 Oct 2026 is a Thursday


# ---------------------------------------------------------------- drivers


def test_drivers_match_the_hand_computed_attribution_and_sum_to_the_change(client, shop) -> None:
    body = get(client, shop, "/analytics/drivers", **PERIOD).json()
    effects = {e["key"]: dec(e["amount"]) for e in body["effects"]}
    assert effects == {
        "volume": D("-375.00"),
        "mix": D("275.00"),
        "price": D("100.00"),
        "new_discontinued": D("300.00"),
        "discounts": D("10.00"),
    }
    assert dec(body["net_change"]) == D("310.00")
    assert sum(effects.values()) == dec(body["net_change"])
    assert dec(body["net_sales_current"]) - dec(body["net_sales_previous"]) == dec(
        body["net_change"]
    )
    assert (body["continuing_products"], body["new_products"], body["discontinued_products"]) == (
        2,
        1,
        0,
    )
    assert "not why" in body["caveat"] or "not why customers" in body["caveat"]

    cont = {r["key"]: dec(r["share_of_change"]) for r in body["contributions"]}
    assert cont["Staples"] == D("-129.03") or abs(cont["Staples"] - D("-129.03")) < D("0.01")
    assert [m["sku"] for m in body["biggest_decliners"]] == ["ATT"]
    assert {m["sku"] for m in body["biggest_gainers"]} == {"GHE", "TEA"}


def test_drivers_contribution_by_other_dimensions(client, shop) -> None:
    body = get(client, shop, "/analytics/drivers", by="channel", **PERIOD).json()
    assert body["contribution_dimension"] == "channel"
    assert sum(dec(r["delta"]) for r in body["contributions"]) == D("310.00")
    body = get(client, shop, "/analytics/drivers", by="product", **PERIOD).json()
    assert {r["key"] for r in body["contributions"]} == {"ATT", "GHE", "TEA"}


def test_insights_are_attributional_and_carry_evidence(client, shop) -> None:
    insights = get(client, shop, "/analytics/overview", **PERIOD).json()["insights"]
    head = next(i for i in insights if i["id"] == "headline")
    assert head["tone"] == "good"
    assert "rose" in head["title"]
    assert "₹2,760" in head["title"]
    assert "not proof of its cause" in head["body"]
    assert all(i["evidence"] for i in insights)
    assert not any(
        "because" in i["body"].lower() or "caused" in i["body"].lower() for i in insights
    )


# ---------------------------------------------------------------- filters


def test_category_filter_equals_independent_calculation(client, shop) -> None:
    body = get(client, shop, "/analytics/overview", category="Staples", **PERIOD).json()
    k = kpis(body)
    assert dec(k["net_sales"]["value"]) == D("1100.00")
    assert dec(k["orders"]["value"]) == 2  # C-1 and C-3
    assert dec(k["net_sales"]["previous"]) == D("1500.00")
    assert body["meta"]["filters"]["categories"] == ["Staples"]


def test_region_and_channel_filters(client, shop) -> None:
    k = kpis(get(client, shop, "/analytics/overview", region="GJ", **PERIOD).json())
    assert dec(k["net_sales"]["value"]) == D("760.00")
    assert dec(k["orders"]["value"]) == 1
    k = kpis(get(client, shop, "/analytics/overview", channel="Phone", **PERIOD).json())
    assert dec(k["net_sales"]["value"]) == D("520.00")
    k = kpis(get(client, shop, "/analytics/overview", region="Unspecified", **PERIOD).json())
    assert dec(k["net_sales"]["value"]) == D("600.00")  # the walk-in order


def test_multiple_filter_values_and_sku(client, shop) -> None:
    k = kpis(
        get(client, shop, "/analytics/overview", category=["Staples", "Beverages"], **PERIOD).json()
    )
    assert dec(k["net_sales"]["value"]) == D("1400.00")
    k = kpis(get(client, shop, "/analytics/overview", sku="GHE", **PERIOD).json())
    assert dec(k["net_sales"]["value"]) == D("1360.00")


# ---------------------------------------------------------------- comparison modes and edge cases


def test_no_comparison_mode(client, shop) -> None:
    body = get(client, shop, "/analytics/overview", compare="none", **PERIOD).json()
    assert body["meta"]["compare"] is None
    k = kpis(body)
    assert k["net_sales"]["previous"] is None
    assert k["net_sales"]["change"] is None
    assert all(p["previous_net"] is None for p in body["trend"])
    assert body["insights"][0]["tone"] == "neutral"


def test_previous_year_with_no_data_degrades_gracefully(client, shop) -> None:
    body = get(client, shop, "/analytics/overview", compare="previous_year", **PERIOD).json()
    assert body["meta"]["compare"]["date_from"] == "2025-10-02"  # 364 days earlier
    assert body["meta"]["compare"]["date_to"] == "2025-10-08"
    k = kpis(body)
    assert dec(k["net_sales"]["value"]) == D("2760.00")
    assert k["net_sales"]["change"] is None  # never a divide-by-zero or infinity
    assert any("comparison period has no sales" in w for w in body["warnings"])


def test_empty_period_returns_zeros_not_errors(client, shop) -> None:
    body = get(
        client, shop, "/analytics/overview", **{"from": "2026-12-01", "to": "2026-12-07"}
    ).json()
    k = kpis(body)
    assert dec(k["net_sales"]["value"]) == D("0.00")
    assert k["aov"]["value"] is None
    assert k["gross_margin"]["value"] is None
    assert len(body["trend"]) == 7
    assert any("no completed orders" in w for w in body["warnings"])


def test_single_day_period(client, shop) -> None:
    body = get(
        client, shop, "/analytics/overview", **{"from": "2026-10-01", "to": "2026-10-01"}
    ).json()
    assert dec(kpis(body)["net_sales"]["value"]) == D("1640.00")
    assert len(body["trend"]) == 1


def test_granularity_week_and_month(client, shop) -> None:
    week = get(
        client,
        shop,
        "/analytics/overview",
        granularity="week",
        **{"from": "2026-09-21", "to": "2026-10-11"},
    ).json()
    assert [p["start"] for p in week["trend"]] == ["2026-09-21", "2026-09-28", "2026-10-05"]
    assert sum(dec(p["net"]) for p in week["trend"]) == D(
        "5210.00"
    )  # 2450 + 2760; the returned order on 6 Oct is not counted
    month = get(
        client,
        shop,
        "/analytics/overview",
        granularity="month",
        **{"from": "2026-09-01", "to": "2026-10-31"},
    ).json()
    assert [dec(p["net"]) for p in month["trend"]] == [D("2450.00"), D("2760.00")]


def test_invalid_inputs(client, shop) -> None:
    r = get(client, shop, "/analytics/overview", **{"from": "2026-10-08", "to": "2026-10-01"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_range"
    assert get(client, shop, "/analytics/overview", compare="sideways", **PERIOD).status_code == 422
    assert get(client, shop, "/analytics/drivers", by="colour", **PERIOD).status_code == 422
    r = get(client, shop, "/analytics/overview", **{"from": "2020-01-01", "to": "2026-10-01"})
    assert r.status_code == 422


def test_empty_workspace(client, make_user) -> None:
    h = make_user("fresh@shop.in")
    ws_id = client.post("/api/v1/workspaces", json={"name": "Fresh"}, headers=h).json()["id"]
    body = client.get(f"/api/v1/workspaces/{ws_id}/analytics/overview", headers=h).json()
    assert body["meta"]["has_data"] is False
    assert "No sales data has been imported yet." in body["warnings"]
    assert dec(kpis(body)["net_sales"]["value"]) == D("0.00")
    opts = client.get(f"/api/v1/workspaces/{ws_id}/analytics/filters", headers=h).json()
    assert opts["has_data"] is False
    assert opts["categories"] == []


# ---------------------------------------------------------------- drill-through


def test_transactions_reconcile_with_the_overview(client, shop) -> None:
    body = get(client, shop, "/analytics/transactions", **PERIOD).json()
    assert body["total_lines"] == 5
    assert dec(body["total_net"]) == D("2760.00")
    assert sum(dec(r["net"]) for r in body["items"]) == D("2760.00")
    assert body["items"][0]["date"] == "2026-10-05"  # newest first
    assert {r["order_id"] for r in body["items"]} == {"C-1", "C-2", "C-3", "C-4"}


def test_transactions_search_filter_and_pagination(client, shop) -> None:
    body = get(client, shop, "/analytics/transactions", search="tea", **PERIOD).json()
    assert body["total_lines"] == 1
    assert body["items"][0]["sku"] == "TEA"
    assert dec(body["total_net"]) == D("300.00")
    page = get(client, shop, "/analytics/transactions", limit=2, offset=2, **PERIOD).json()
    assert len(page["items"]) == 2
    assert page["total_lines"] == 5
    body = get(client, shop, "/analytics/transactions", category="Dairy", **PERIOD).json()
    assert dec(body["total_net"]) == D("1360.00")
    assert get(client, shop, "/analytics/transactions", limit=500, **PERIOD).status_code == 422


# ---------------------------------------------------------------- tenancy and roles


def test_other_workspaces_cannot_read_analytics(client, shop, make_user) -> None:
    _, ws_id = shop
    outsider = make_user("outsider@else.in")
    for path in (
        "/metrics",
        "/analytics/filters",
        "/analytics/overview",
        "/analytics/drivers",
        "/analytics/transactions",
    ):
        r = client.get(f"/api/v1/workspaces/{ws_id}{path}", headers=outsider)
        assert r.status_code == 404, path


def test_viewer_can_read_and_data_never_leaks_between_tenants(client, shop, make_user) -> None:
    h, ws_id = shop
    viewer = make_user("viewer@analytics.in")
    client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "viewer@analytics.in", "role": "viewer"},
        headers=h,
    )
    r = client.get(f"/api/v1/workspaces/{ws_id}/analytics/overview", params=PERIOD, headers=viewer)
    assert r.status_code == 200
    assert dec(kpis(r.json())["net_sales"]["value"]) == D("2760.00")

    other = make_user("other@owner.in")
    other_ws = client.post("/api/v1/workspaces", json={"name": "Other"}, headers=other).json()["id"]
    body = client.get(
        f"/api/v1/workspaces/{other_ws}/analytics/overview", params=PERIOD, headers=other
    ).json()
    assert dec(kpis(body)["net_sales"]["value"]) == D("0.00")  # nothing from the other shop


def test_requires_authentication(client, shop) -> None:
    _, ws_id = shop
    assert client.get(f"/api/v1/workspaces/{ws_id}/analytics/overview").status_code == 401


# ---------------------------------------------------------------- realistic data


SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample" / "vyapar_demo_sales.csv"


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample data not generated")
def test_everything_reconciles_on_the_8k_row_sample(client: TestClient, make_user) -> None:
    h = make_user("big@shop.in")
    ws_id = client.post("/api/v1/workspaces", json={"name": "Big"}, headers=h).json()["id"]
    _, base, summary = full_flow(client, h, ws_id, SAMPLE.read_bytes(), "sample.csv")
    assert summary["rows_invalid"] == 0
    client.post(f"{base}/import", headers=h)

    period = {"from": "2026-09-01", "to": "2026-10-31"}
    ov = client.get(
        f"/api/v1/workspaces/{ws_id}/analytics/overview", params=period, headers=h
    ).json()
    net = dec(kpis(ov)["net_sales"]["value"])
    assert net > 0
    assert abs(sum(dec(p["net"]) for p in ov["trend"]) - net) <= D("0.50")
    assert sum(dec(r["net"]) for r in ov["category_mix"]) == net
    assert sum(dec(r["net"]) for r in ov["channel_mix"]) == net
    assert sum(dec(r["net"]) for r in ov["region_mix"]) == net

    dr = client.get(
        f"/api/v1/workspaces/{ws_id}/analytics/drivers", params=period, headers=h
    ).json()
    assert sum(dec(e["amount"]) for e in dr["effects"]) == dec(dr["net_change"])
    assert dec(dr["net_sales_current"]) - dec(dr["net_sales_previous"]) == dec(dr["net_change"])

    # the summary on the data page agrees with the metric layer over the whole history
    whole = client.get(
        f"/api/v1/workspaces/{ws_id}/analytics/overview",
        params={"from": "2026-08-01", "to": "2026-10-31", "compare": "none"},
        headers=h,
    ).json()
    summary_total = client.get(f"/api/v1/workspaces/{ws_id}/data-summary", headers=h).json()
    assert dec(kpis(whole)["net_sales"]["value"]) == dec(summary_total["net_sales_completed"])

    tx = client.get(
        f"/api/v1/workspaces/{ws_id}/analytics/transactions",
        params={**period, "limit": 5},
        headers=h,
    ).json()
    assert dec(tx["total_net"]) == net
