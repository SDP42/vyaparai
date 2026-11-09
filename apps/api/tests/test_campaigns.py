"""Campaign planning checked against the hand-computed customer fixture.

Fixture (see test_intelligence_api): every sale carries a 40 % margin (cost is 60 % of rate).
Segments at 2026-10-31: A Loyal, B Champions, C Hibernating, D New, E At risk, F New.
E bought on 10 Aug and 25 Aug (gap 15 days), not since: 67 days ago, so 67/15 = 4.47x overdue.
Product SKU1 over the window: net 2130 on 12 units, margin 40 %.
"""

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services import campaigns
from tests.test_intelligence_api import CUSTOMERS_CSV, make_shop

D = Decimal


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "camp@shop.in", CUSTOMERS_CSV)


def get(client: TestClient, shop, path: str, **params):
    h, ws_id = shop
    return client.get(f"/api/v1/workspaces/{ws_id}/campaigns{path}", params=params, headers=h)


# ---------------------------------------------------------------- pure rules


def test_safe_discount_keeps_the_margin_floor() -> None:
    # margin 40 %, floor 15 %: d <= 1 - 0.60/0.85 = 29.41 %
    assert campaigns.max_safe_discount(D(40), D(15)).quantize(D("0.01")) == D("29.41")
    assert campaigns.max_safe_discount(D(40), D(35)).quantize(D("0.01")) == D("7.69")
    assert campaigns.max_safe_discount(D(10), D(15)) == 0  # already below the floor: no discount
    assert campaigns.max_safe_discount(None, D(15)) == 0  # unknown cost: no discount
    # the margin after a safe discount lands exactly on the floor
    d = campaigns.max_safe_discount(D(40), D(15))
    assert campaigns.margin_after(D(40), d) == D("15.00")


def test_margin_after_a_discount() -> None:
    assert campaigns.margin_after(D(40), D(10)) == D("33.33")  # 1 - 0.6/0.9
    assert campaigns.margin_after(D(40), D(0)) == D("40.00")


def test_holdout_is_stable_and_respects_zero() -> None:
    assert campaigns.in_holdout("At risk", "C-1", 0) is False
    runs = [campaigns.in_holdout("At risk", f"C-{i}", 20) for i in range(500)]
    assert runs == [campaigns.in_holdout("At risk", f"C-{i}", 20) for i in range(500)]
    assert 0.12 <= sum(runs) / 500 <= 0.28  # about 20 %


def test_ladder_escalates_and_never_opens_with_the_deepest_offer() -> None:
    steps = campaigns.ladder(campaigns.PLAYS["At risk"], D(12))
    assert [s["discount_pct"] for s in steps] == [0, 6, 12]
    assert campaigns.ladder(campaigns.PLAYS["Champions"], D(0)) == [
        {"step": 1, "name": "Friendly message", "discount_pct": 0, "when": "Day 0"}
    ]


# ---------------------------------------------------------------- API


def test_playbook_counts_every_segment(client: TestClient, shop) -> None:
    r = get(client, shop, "/playbook", as_of="2026-10-31").json()
    counts = {e["segment"]: e["customers"] for e in r}
    assert counts == {
        "Champions": 1, "Loyal": 1, "New": 2, "Promising": 0,
        "Needs attention": 0, "Can't lose": 0, "At risk": 1, "Hibernating": 1,
    }  # fmt: skip
    assert len(r) == 8


def test_at_risk_plan_matches_hand_computed_values(client: TestClient, shop) -> None:
    p = get(client, shop, "/plan", segment="At risk", as_of="2026-10-31", holdout_pct=0).json()
    assert p["audience"] == {"total": 1, "contact": 1, "holdout": 0}
    row = p["rows"][0]
    assert row["key"] == "E"
    assert row["recency_days"] == 67
    assert D(row["overdue_ratio"]) == D("4.47")
    assert "4.47" in row["reason"]
    assert row["consent_status"] == "not_recorded"
    offer = p["offers"][0]
    assert offer["sku"] == "SKU1"
    assert D(offer["margin_pct"]) == D("40.00")
    assert D(offer["price"]) == D("177.50")
    assert D(offer["discount_pct"]) == 12  # the play's ceiling; the safe limit is 29
    assert D(offer["safe_discount_pct"]) == 29
    assert D(offer["margin_after_pct"]) == D("31.82")  # 1 - 0.6/0.88
    proj = p["projection"]
    assert D(proj["expected_redeemers"]) == D("0.08")  # 1 contact x 8 % assumed
    assert D(proj["avg_order_value"]) == D("150.00")  # E: 300 over 2 orders
    assert D(proj["expected_sales"]) == D("12.00")
    assert D(proj["expected_discount_given"]) == D("1.64")  # 12 x 12/88
    assert [s["discount_pct"] for s in p["ladder"]] == [0, 6, 12]
    assert "12% off" in row["message"]
    assert row["message"].endswith("Reply STOP to opt out.")
    assert "assumption" in proj["note"].lower()
    assert "consent" in p["consent_note"].lower()


def test_a_higher_margin_floor_shrinks_the_offer(client: TestClient, shop) -> None:
    p = get(
        client, shop, "/plan", segment="At risk", as_of="2026-10-31", holdout_pct=0, margin_floor=35
    ).json()
    offer = p["offers"][0]
    assert D(offer["discount_pct"]) == 7  # floor 35 % leaves room for only 7 %
    assert D(offer["margin_after_pct"]) == D("35.48")  # 1 - 0.6/0.93
    assert D(offer["margin_after_pct"]) >= 35  # never below the floor
    higher = get(
        client, shop, "/plan", segment="At risk", as_of="2026-10-31", holdout_pct=0, margin_floor=40
    ).json()
    assert D(higher["offers"][0]["discount_pct"]) == 0  # margin already at the floor: no discount


def test_champions_get_a_thank_you_and_no_discount(client: TestClient, shop) -> None:
    p = get(client, shop, "/plan", segment="Champions", as_of="2026-10-31", holdout_pct=0).json()
    assert p["params"]["max_discount"] == 0
    assert D(p["offers"][0]["discount_pct"]) == 0
    assert len(p["ladder"]) == 1
    assert "Thank you" in p["rows"][0]["message"]


def test_hinglish_messages_and_opt_out_line(client: TestClient, shop) -> None:
    p = get(
        client,
        shop,
        "/plan",
        segment="At risk",
        as_of="2026-10-31",
        holdout_pct=0,
        language="hinglish",
    ).json()
    msg = p["rows"][0]["message"]
    assert "kaafi time ho gaya" in msg
    assert msg.endswith("Band karne ke liye STOP likhiye.")


def test_unknown_segment_and_stranger(client: TestClient, shop, make_user) -> None:
    assert get(client, shop, "/plan", segment="Whales").status_code == 422
    stranger = make_user("x@x.in", "X")
    r = client.get(f"/api/v1/workspaces/{shop[1]}/campaigns/playbook", headers=stranger)
    assert r.status_code == 404


def test_without_costs_only_value_messages_are_suggested(client: TestClient, make_user) -> None:
    lines = CUSTOMERS_CSV.strip().splitlines()
    cols = lines[0].split(",")
    cost_i = cols.index("Cost")
    blanked = [lines[0]] + [
        ",".join("" if i == cost_i else v for i, v in enumerate(ln.split(","))) for ln in lines[1:]
    ]
    s = make_shop(client, make_user, "nocost@shop.in", "\n".join(blanked) + "\n")
    p = get(client, s, "/plan", segment="At risk", as_of="2026-10-31", holdout_pct=0).json()
    assert p["offers"][0]["flag"] == "no_cost"
    assert D(p["offers"][0]["discount_pct"]) == 0
    assert "% off" not in p["rows"][0]["message"]
    assert any("No cost is recorded" in w for w in p["warnings"])


def test_export_lists_everyone_marks_holdout_and_is_audited(client: TestClient, shop) -> None:
    h, ws_id = shop
    r = get(client, shop, "/export.csv", segment="New", as_of="2026-10-31", holdout_pct=30)
    assert r.status_code == 200
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("customer,group,segment")
    assert len(lines) == 1 + 2  # D and F
    groups = {ln.split(",")[1] for ln in lines[1:]}
    assert groups <= {"contact", "holdout"}
    for ln in lines[1:]:
        if ",holdout," in ln:
            assert ln.rstrip().endswith(",")  # holdout customers get no message text
    logs = client.get(f"/api/v1/workspaces/{ws_id}/audit-logs", headers=h).json()
    assert any(x["action"] == "campaign.exported" for x in logs["items"])


SAMPLE = Path(__file__).resolve().parents[3] / "data" / "sample" / "vyapar_demo_sales.csv"


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample data not generated")
def test_holdout_share_and_totals_on_the_sample(client: TestClient, make_user) -> None:
    s = make_shop(client, make_user, "bigc@shop.in", SAMPLE.read_text())
    book = get(client, s, "/playbook").json()
    biggest = max(book, key=lambda e: e["customers"])
    assert sum(e["customers"] for e in book) > 100
    p = get(client, s, "/plan", segment=biggest["segment"], holdout_pct=30, limit=200).json()
    a = p["audience"]
    assert a["total"] == biggest["customers"]
    assert a["contact"] + a["holdout"] == a["total"]
    assert 0.15 <= a["holdout"] / a["total"] <= 0.45  # about 30 %
    assert p["total_rows"] == a["total"]  # every customer is listed, holdout ones are flagged
    assert sum(r["holdout"] for r in p["rows"]) == a["holdout"]
    again = get(client, s, "/plan", segment=biggest["segment"], holdout_pct=30, limit=200).json()
    assert [r["key"] for r in again["rows"]] == [r["key"] for r in p["rows"]]  # stable groups
    for o in p["offers"]:
        if o["margin_after_pct"] is None:
            continue
        if D(o["discount_pct"]) > 0:
            assert D(o["margin_after_pct"]) >= 15  # an offered discount never breaks the floor
        elif D(o["margin_pct"]) < 15:
            assert D(o["discount_pct"]) == 0  # products already under the floor get no discount
