# ruff: noqa: E501
"""Pricing advice on planted data: a discount that lifts profit, one that does not, and a price rise that did not hurt volume."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.services import pricing
from tests.test_intelligence_api import make_shop

START = date(2026, 6, 1)
DAYS = 120


def csv_text() -> str:
    """Three products over 120 days.

    GOOD: 10 a day at 100 (cost 60); every 10th day 20% off and 25 sold  -> profit 500 vs 400: paid off.
    BAD:  10 a day at 100 (cost 60); every 10th day 20% off and still 10  -> profit 200 vs 400: lost money.
    RISE: 10 a day at 100 for 8 weeks, then 110 and still 10 a day       -> a lasting price move with no volume loss.
    """
    rows = [
        "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status"
    ]
    for i in range(DAYS):
        d = START + timedelta(days=i)
        ds = d.strftime("%d/%m/%Y")
        promo = i % 10 == 9
        rows.append(
            f"G{i},{ds},GOOD,Good Biscuit,Cat,{25 if promo else 10},100,{500 if promo else 0},60,C1,MH,Pune,Store,Paid"
        )
        rows.append(
            f"B{i},{ds},BAD,Bad Soap,Cat,10,100,{200 if promo else 0},60,C2,MH,Pune,Store,Paid"
        )
        rows.append(
            f"R{i},{ds},RISE,Rising Tea,Cat,10,{100 if i < 56 else 110},0,60,C3,MH,Pune,Store,Paid"
        )
    return "\n".join(rows) + "\n"


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "price@shop.in", csv_text())


def test_judge_needs_enough_promo_and_normal_days() -> None:
    few = [pricing.Day(START + timedelta(days=i), 10, 1000, 0, 600, 1000) for i in range(10)]
    assert pricing.judge_discounts(few, START, START + timedelta(days=9)) is None


def test_discounts_that_lift_profit_are_found_and_those_that_do_not_are_flagged(
    client: TestClient, shop
) -> None:
    h, ws = shop
    r = client.get(f"/api/v1/workspaces/{ws}/pricing/discounts", headers=h).json()
    by = {i["sku"]: i for i in r["items"]}
    good, bad = by["GOOD"], by["BAD"]
    assert good["verdict"] == "paid_off"
    assert good["lift_pct"] == pytest.approx(150, abs=1)
    assert good["profit_effect_low"] > 0
    assert bad["verdict"] == "lost_money"
    assert bad["lift_pct"] == pytest.approx(0, abs=1)
    assert bad["profit_effect"] == pytest.approx(-200 * bad["promo_days"], rel=0.01)
    assert bad["discount_given"] == pytest.approx(200 * bad["promo_days"])
    assert "RISE" not in by  # no discount days: not judged
    assert r["items"][0]["sku"] == "BAD"  # losing promotions first
    assert r["summary"]["lost_money"] == 1
    assert r["summary"]["paid_off"] == 1
    assert r["limits"]


def test_a_lasting_price_rise_is_detected_with_its_volume_response(
    client: TestClient, shop
) -> None:
    h, ws = shop
    m = client.get(f"/api/v1/workspaces/{ws}/pricing/moves", headers=h).json()
    rise = [x for x in m["moves"] if x["sku"] == "RISE"]
    assert len(rise) == 1
    assert rise[0]["old_price"] == pytest.approx(100, abs=0.5)
    assert rise[0]["new_price"] == pytest.approx(110, abs=0.5)
    assert rise[0]["price_pct"] == pytest.approx(10, abs=0.5)
    assert rise[0]["units_pct"] == pytest.approx(0, abs=1)
    assert rise[0]["elasticity"] == pytest.approx(0, abs=0.2)
    assert rise[0]["reliable"] is True


def test_suggestions_use_a_measured_response_when_there_is_one_and_ranges_when_not() -> None:
    measured = pricing.suggest("X", 100, 90, 300, -0.2)
    assert measured is not None
    assert measured["measured"] is True
    assert measured["assumption"] is None
    assumed = pricing.suggest("X", 100, 90, 300, None)
    assert assumed is not None
    assert assumed["measured"] is False
    assert "assumed" in assumed["assumption"]
    lo, hi = assumed["profit_change_month"]["low"], assumed["profit_change_month"]["high"]
    assert lo < hi
    assert (
        pricing.suggest("X", 100, 120, 300, None) is None
    )  # selling below cost: nothing to suggest
    assert pricing.suggest("X", 100, None, 300, None) is None  # no cost: cannot judge profit


def test_a_thin_margin_product_gets_a_small_trial_not_a_big_jump(client: TestClient, shop) -> None:
    h, ws = shop
    m = client.get(f"/api/v1/workspaces/{ws}/pricing/moves", headers=h).json()
    assert all(s["step_pct"] <= 3 for s in m["suggestions"])


def test_the_recommendation_engine_picks_up_the_losing_discount(client: TestClient, shop) -> None:
    h, ws = shop
    client.post(f"/api/v1/workspaces/{ws}/recommendations/refresh", headers=h)
    recs = client.get(f"/api/v1/workspaces/{ws}/recommendations", headers=h).json()
    stop = [r for r in recs if r["kind"] == "stop_discount"]
    assert len(stop) == 1
    assert "Bad Soap" in stop[0]["title"]
    assert stop[0]["impact"]["measured"] is True
    assert stop[0]["impact"]["low"] <= stop[0]["impact"]["expected"] <= stop[0]["impact"]["high"]


def test_empty_workspace_and_permissions(client: TestClient, make_user, shop) -> None:
    h = make_user("e@shop.in")
    ws = client.post("/api/v1/workspaces", json={"name": "Empty"}, headers=h).json()["id"]
    assert (
        client.get(f"/api/v1/workspaces/{ws}/pricing/discounts", headers=h).json()["has_data"]
        is False
    )
    assert (
        client.get(f"/api/v1/workspaces/{ws}/pricing/moves", headers=h).json()["has_data"] is False
    )
    stranger = make_user("s@s.in")
    assert (
        client.get(f"/api/v1/workspaces/{shop[1]}/pricing/discounts", headers=stranger).status_code
        == 404
    )
