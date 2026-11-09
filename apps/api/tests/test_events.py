# ruff: noqa: E501
"""Events: dates, ramps, regions, product matching, calendar and the stock-at-risk view.

Ramp for an event on 10 Jan with 4 lead days and 2 tail days:
  5 Jan 0 (outside) | 6 Jan 0.3 + 0.7 x (1 - 4/5) = 0.44 | 9 Jan 0.3 + 0.7 x (1 - 1/5) = 0.86 | 10 Jan 1.0
  11 Jan 1 - 1/3 = 0.667 | 12 Jan 1 - 2/3 = 0.333 | 13 Jan 0 (past the tail)
"""

from datetime import date, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.services import events, events_insight
from tests.test_intelligence_api import make_shop


def ev(**kw) -> events.Event:
    base = {"id": "x", "name": "X", "start": date(2027, 1, 10), "end": date(2027, 1, 10), "category": "festival", "tier": 1,
            "scope": "national", "regions": frozenset({"all"}), "lead": 4, "tail": 2, "demand": ("staples",),
            "notes": "", "basis": "gazette", "confidence": "high", "sources": ()}  # fmt: skip
    return events.Event(**{**base, **kw})


# ---------------------------------------------------------------- the table


def test_the_table_loads_and_is_consistent() -> None:
    all_ = events.load()
    assert len(all_) >= 100
    assert len({e.id for e in all_}) == len(all_)
    assert all(e.end >= e.start and e.tier in (1, 2, 3) for e in all_)
    cov = events.coverage()
    assert cov["first"] <= date(2026, 11, 9)
    assert cov["last"] >= date(2028, 6, 1)
    assert sum(cov["by_confidence"].values()) == cov["events"]


def test_known_dates_match_the_gazette() -> None:
    by = {e.id: e for e in events.load()}
    assert by["diwali-2027"].start == date(2027, 10, 29)
    assert by["dussehra-2027"].start == date(2027, 10, 9)
    assert by["christmas-2027"].end == date(2027, 12, 25)
    assert by["wc2027-ind-pak"].start == date(2027, 10, 10)
    assert date(2027, 10, 29) in events.peak_dates()


# ---------------------------------------------------------------- ramps and overlaps


def test_phase_ramps_in_holds_and_fades() -> None:
    e = ev()
    phases = {d: round(e.phase(date(2027, 1, d)), 3) for d in (5, 6, 9, 10, 11, 12, 13)}
    assert phases == {5: 0.0, 6: 0.44, 9: 0.86, 10: 1.0, 11: 0.667, 12: 0.333, 13: 0.0}


def test_weights_and_caps() -> None:
    assert ev(tier=1).weight == 1.0
    assert ev(tier=2).weight == 0.6
    assert ev(tier=3).weight == 0.25
    assert (
        ev(tier=1, category="season").weight == 0.4
    )  # background context weighs less than a festival
    assert ev(tier=1, category="holiday").weight == 0.5


def test_overlapping_events_do_not_stack(monkeypatch) -> None:
    big, small = (
        ev(id="a", tier=1),
        ev(id="b", tier=2, start=date(2027, 1, 9), end=date(2027, 1, 11)),
    )
    monkeypatch.setattr(events, "load", lambda: (big, small))
    vals = events.intensity([date(2027, 1, 10)])
    assert vals[0] == 1.0  # the strongest, not 1.0 + 0.6


def test_cricket_is_a_separate_signal(monkeypatch) -> None:
    cup = ev(id="c", category="cricket", tier=1, start=date(2027, 10, 2), end=date(2027, 11, 21))
    monkeypatch.setattr(events, "load", lambda: (cup,))
    flags = events.cricket_flag([date(2027, 10, 1), date(2027, 10, 10), date(2027, 11, 22)])
    assert list(flags) == [0.0, 1.0, 0.0]
    assert events.intensity([date(2027, 10, 10)])[0] == 0.0  # cricket is not a festival intensity


# ---------------------------------------------------------------- regions


def test_listed_regions_decide_not_the_scope() -> None:
    south = ev(scope="regional", regions=frozenset({"kerala", "south"}))
    north_national = ev(scope="national", regions=frozenset({"north", "west", "central"}))
    anywhere = ev(regions=frozenset({"all"}))
    kerala = events.zones_for("Kerala")
    assert south.applies(kerala, "Kerala")
    assert not south.applies(events.zones_for("Maharashtra"), "Maharashtra")
    assert not north_national.applies(
        kerala, "Kerala"
    )  # a "national" festival limited to the north
    assert north_national.applies(events.zones_for("Maharashtra"), "Maharashtra")  # west
    assert north_national.applies(
        events.zones_for("Uttar Pradesh"), "Uttar Pradesh"
    )  # north and central
    assert anywhere.applies(frozenset(), None)
    assert not south.applies(frozenset(), None)  # unknown location: regional events are left out
    assert north_national.applies(
        frozenset(), None
    )  # but a national one is kept until we know better


def test_a_state_in_two_zones_matches_both() -> None:
    assert events.zones_for("Rajasthan") == {"north", "west"}
    assert events.zones_for("Chhattisgarh") == {"central", "east"}
    assert events.zones_for("Atlantis") == frozenset()


# ---------------------------------------------------------------- products and covariates


def test_products_map_to_demand_categories() -> None:
    assert events.demand_categories("Desi Ghee 1 L", "Dairy") == {"dairy", "oil_ghee_sugar"}
    assert events.demand_categories("Toor Dal 1 kg", "Staples") == {"staples"}
    assert events.demand_categories("Potato Chips 52 g", "Snacks") == {"beverages_snacks"}
    assert "fasting_foods" in events.demand_categories("Sabudana 500 g", "Staples")
    assert events.demand_categories("Widget", None) == set()


def test_covariates_cover_history_plus_forecast_days() -> None:
    dates = [date(2027, 10, 1) + timedelta(days=i) for i in range(40)]
    cov = events.covariates(dates, 14)
    assert cov is not None
    assert len(cov["event_intensity"]) == 54
    assert len(cov["cricket"]) == 54
    assert cov["cricket"][9] == 1.0  # 10 Oct 2027, India v Pakistan at the World Cup
    assert cov["event_intensity"].max() <= 1.0
    assert (
        events.covariates([date(2010, 1, 1) + timedelta(days=i) for i in range(30)], 14) is None
    )  # outside the table


# ---------------------------------------------------------------- API


NAMES = [
    ("SKU-A", "Atta 5 kg", "Staples"),
    ("SKU-G", "Desi Ghee 1 L", "Dairy"),
    ("SKU-C", "Potato Chips", "Snacks"),
    ("SKU-S", "Bath Soap", "Personal care"),
]


def shop_csv() -> str:
    head = "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status"
    lines = [head]
    d = date(2026, 9, 1)
    while d <= date(2026, 10, 25):
        for sku, name, cat in NAMES:
            lines.append(f"{sku}{d:%m%d},{d:%d/%m/%Y},{sku},{name},{cat},10,100,0,60,,,,Store,Paid")
        d += timedelta(days=1)
    return "\n".join(lines) + "\n"


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "ev@shop.in", shop_csv())


def url(shop, path, **params):
    return f"/api/v1/workspaces/{shop[1]}/events{path}"


def test_calendar_filters_by_tier_cricket_and_region(client: TestClient, shop) -> None:
    h, window = shop[0], {"from": "2027-09-01", "to": "2027-11-30"}
    ids = lambda r: {e["id"] for e in r}  # noqa: E731
    base = client.get(url(shop, "/calendar"), params={**window, "tier_max": 1}, headers=h).json()
    assert {"diwali-2027", "dussehra-2027", "wc2027-window"} <= ids(base)
    assert "onam-2027" not in ids(base)  # Kerala only; the shop has no location yet
    assert "karwa-chauth-2027" not in ids(
        base
    )  # a north, west and central festival: hidden until we know the city
    no_cricket = client.get(
        url(shop, "/calendar"),
        params={**window, "tier_max": 1, "include_cricket": "false"},
        headers=h,
    ).json()
    assert "wc2027-window" not in ids(no_cricket)
    assert "diwali-2027" in ids(no_cricket)
    client.put(f"/api/v1/workspaces/{shop[1]}/weather/location", json={"city": "Pune"}, headers=h)
    pune = client.get(url(shop, "/calendar"), params={**window, "tier_max": 1}, headers=h).json()
    assert "karwa-chauth-2027" in ids(pune)  # Pune is in the west
    client.put(f"/api/v1/workspaces/{shop[1]}/weather/location", json={"city": "Kochi"}, headers=h)
    kochi = client.get(url(shop, "/calendar"), params={**window, "tier_max": 1}, headers=h).json()
    assert "onam-2027" in ids(kochi)  # now it applies
    assert "durga-puja-2027" not in ids(kochi)  # east India only
    assert "karwa-chauth-2027" not in ids(kochi)  # celebrated in the north, west and centre


def test_upcoming_lists_matching_products_and_flags_stock_at_risk(
    client: TestClient, shop, db_session_factory
) -> None:
    from app.models.workspace import Workspace

    h = shop[0]
    client.post(
        f"/api/v1/workspaces/{shop[1]}/inventory/import",
        files={"file": ("s.csv", b"SKU,Stock\nSKU-A,10\nSKU-G,5000\n", "text/csv")},
        data={"as_of": "2026-10-25"},
        headers=h,
    )
    import uuid

    with db_session_factory() as db:
        ws = db.get(Workspace, uuid.UUID(shop[1]))
        rows = events_insight.upcoming(
            db, ws, days=40, include_cricket=False, today=date(2027, 10, 20)
        )
    diwali = next(r for r in rows if r["event"].id == "diwali-season-2027")
    assert diwali["status"] == "ramping"  # 7 days out, inside the 21-day lead
    assert diwali["days_until"] == 7
    by = {p["sku"]: p for p in diwali["products"]}
    assert {"SKU-A", "SKU-G"} <= set(
        by
    )  # atta (staples) and ghee (oil_ghee_sugar) are on Diwali's list
    assert by["SKU-A"]["at_risk"] is True  # 10 units at about 10 a day will not last the festival
    assert by["SKU-G"]["at_risk"] is False  # 5,000 units will
    assert by["SKU-A"]["tracked"] is True


def test_upcoming_endpoint_and_coverage_and_tenancy(client: TestClient, shop, make_user) -> None:
    h = shop[0]
    r = client.get(url(shop, "/upcoming"), params={"days": 365}, headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    cov = client.get(url(shop, "/coverage"), headers=h).json()
    assert cov["events"] >= 100
    stranger = make_user("s@x.in", "S")
    assert client.get(url(shop, "/upcoming"), headers=stranger).status_code == 404
    assert client.get(url(shop, "/upcoming"), params={"days": 3}, headers=h).status_code == 422


def test_effects_need_history_and_say_nothing_when_there_is_none(client: TestClient, shop) -> None:
    r = client.get(url(shop, "/effects"), headers=shop[0]).json()
    for row in r:
        assert row["all_products"] is None or row["all_products"]["ratio"] > 0
    assert client.get(url(shop, "/effects"), headers=shop[0]).status_code == 200


def test_effects_measure_a_real_lift_exactly(client: TestClient, make_user) -> None:
    """Sales are 10 a day, and 20 a day inside the Diwali 2025 window: the lift must come out as 2.0."""
    diwali = next(e for e in events.load() if e.id == "diwali-2025")
    lo, hi = events.window(diwali)
    head = "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status"
    lines = [head]
    d = lo - timedelta(days=35)
    while d <= hi + timedelta(days=5):
        qty = 20 if lo <= d <= hi else 10
        lines.append(
            f"B{d:%y%m%d},{d:%d/%m/%Y},SKU-G,Desi Ghee 1 L,Dairy,{qty},100,0,60,,,,Store,Paid"
        )
        d += timedelta(days=1)
    s = make_shop(client, make_user, "lift@shop.in", "\n".join(lines) + "\n")
    rows = client.get(url(s, "/effects"), headers=s[0]).json()
    row = next(r for r in rows if r["id"] == "diwali-2025")
    assert row["all_products"]["ratio"] == pytest.approx(2.0, abs=0.001)
    assert row["matching_products"]["ratio"] == pytest.approx(
        2.0, abs=0.001
    )  # ghee is on Diwali's list
    assert row["matching_count"] == 1
    assert np.isclose(row["all_products"]["baseline_per_day"], 1000.0)


# ---------------------------------------------------------------- region setting


def relevance_map(client, shop, tier_max=1):
    r = client.get(
        url(shop, "/calendar"),
        params={
            "from": "2027-01-01",
            "to": "2027-12-31",
            "tier_max": tier_max,
            "include_cricket": "false",
        },
        headers=shop[0],
    )
    return {e["id"]: e["relevance"] for e in r.json()}


def window_ids(client, shop, tier_max=1):
    return set(relevance_map(client, shop, tier_max))


def set_state(client, shop, state):
    return client.put(url(shop, "/region"), json={"state": state}, headers=shop[0])


# state -> {festival: expected relevance}; a festival not listed here must be absent
REGION_CASES = [
    ("Kerala", {"onam-2027": "core", "pongal-2027": "zone"}, {"durga-puja-2027", "baisakhi-2027", "karwa-chauth-2027"}),
    ("Tamil Nadu", {"pongal-2027": "core", "onam-2027": "zone"}, {"durga-puja-2027", "baisakhi-2027"}),
    ("West Bengal", {"durga-puja-2027": "core"}, {"onam-2027", "pongal-2027", "baisakhi-2027"}),
    ("Punjab", {"baisakhi-2027": "core", "karwa-chauth-2027": "core"}, {"onam-2027", "durga-puja-2027", "pongal-2027"}),
    ("Maharashtra", {"ganesh-chaturthi-2027": "core", "ugadi-gudi-padwa-2027": "core", "karwa-chauth-2027": "core"}, {"onam-2027", "durga-puja-2027", "baisakhi-2027"}),
    ("Uttar Pradesh", {"karwa-chauth-2027": "core"}, {"onam-2027", "durga-puja-2027", "ganesh-chaturthi-2027"}),
]  # fmt: skip


@pytest.mark.parametrize(("state", "expected", "absent"), REGION_CASES)
def test_each_region_gets_its_own_festivals(
    client: TestClient, shop, state, expected, absent
) -> None:
    assert set_state(client, shop, state).status_code == 200
    got = relevance_map(client, shop)
    for fid, rel in expected.items():
        assert got.get(fid) == rel, (fid, got.get(fid))
    assert not (absent & set(got)), absent & set(got)
    assert got["diwali-2027"] == "core"  # all-India events are always core
    assert got["christmas-2027"] == "core"


def test_zone_relevance_is_weaker_than_core() -> None:
    onam = next(e for e in events.load() if e.id == "onam-2027")
    d = [onam.start]
    kerala = events.intensity(d, events.zones_for("Kerala"), "Kerala")[0]
    tamil = events.intensity(d, events.zones_for("Tamil Nadu"), "Tamil Nadu")[0]
    north = events.intensity(d, events.zones_for("Punjab"), "Punjab")[0]
    assert kerala == 1.0  # the festival's home state
    assert tamil == pytest.approx(0.5)  # observed in the same zone, less strongly
    assert north < 1.0
    assert tamil < kerala


def test_a_state_in_two_zones_gets_both_zones_festivals(client: TestClient, shop) -> None:
    set_state(client, shop, "Rajasthan")  # north and west
    got = relevance_map(client, shop)
    assert (
        got["baisakhi-2027"] == "zone"
    )  # named for Punjab, Haryana and Delhi; Rajasthan is in the north zone
    assert got["karwa-chauth-2027"] == "core"  # lists zones only, and Rajasthan is in two of them
    assert (
        got["ganesh-chaturthi-2027"] == "zone"
    )  # named for other states; Rajasthan is in the west zone
    assert "onam-2027" not in got


def test_regions_endpoint_and_validation(client: TestClient, shop, make_user) -> None:
    r = client.get(url(shop, "/regions"), headers=shop[0]).json()
    assert r["state"] is None
    assert r["zones"] == []
    assert {s["state"] for s in r["states"]} >= {"Kerala", "Punjab", "West Bengal", "Maharashtra"}
    assert set_state(client, shop, "Atlantis").status_code == 422
    assert set_state(client, shop, "Kerala").json() == {"state": "Kerala", "zones": ["south"]}
    assert client.get(url(shop, "/regions"), headers=shop[0]).json()["zones"] == ["south"]
    stranger = make_user("rg@x.in", "R")
    assert (
        client.put(url(shop, "/region"), json={"state": "Kerala"}, headers=stranger).status_code
        == 404
    )


def test_the_state_wins_over_the_city_and_cities_set_it(client: TestClient, shop) -> None:
    client.put(
        f"/api/v1/workspaces/{shop[1]}/weather/location", json={"city": "Pune"}, headers=shop[0]
    )
    assert (
        client.get(url(shop, "/regions"), headers=shop[0]).json()["state"] == "Maharashtra"
    )  # from the city
    set_state(client, shop, "Kerala")
    assert (
        client.get(url(shop, "/regions"), headers=shop[0]).json()["state"] == "Kerala"
    )  # an explicit choice wins
    assert "onam-2027" in window_ids(client, shop)
    ws = client.get(f"/api/v1/workspaces/{shop[1]}", headers=shop[0]).json()
    assert ws["state"] == "Kerala"
    assert ws["city"] == "Pune"


# ---------------------------------------------------------------- alerts for coming festivals


def test_a_coming_festival_with_thin_stock_becomes_a_high_alert(
    client: TestClient, shop, db_session_factory
) -> None:
    import uuid

    from app.models.workspace import Workspace
    from app.services import alerts

    h = shop[0]
    client.post(
        f"/api/v1/workspaces/{shop[1]}/inventory/import",
        files={"file": ("s.csv", b"SKU,Stock\nSKU-G,10\nSKU-A,9000\n", "text/csv")},
        data={"as_of": "2026-10-25"},
        headers=h,
    )
    with db_session_factory() as db:
        ws = db.get(Workspace, uuid.UUID(shop[1]))
        found = alerts.rule_events(db, ws, date(2027, 10, 20))
    keys = {a["key"]: a for a in found}
    diwali = keys["event_ahead|diwali-season-2027"]
    assert diwali["severity"] == "high"  # ghee is on the list and 10 units will not last
    assert "Desi Ghee 1 L" in diwali["detail"]
    assert diwali["evidence"]["at_risk"] >= 1
    assert diwali["link"] == "/app/festivals"
    assert "starts in" in diwali["title"] or "on now" in diwali["title"]
    assert len(found) <= 3


def test_no_festival_alert_when_nothing_is_close_or_nothing_matches(
    client: TestClient, shop, db_session_factory
) -> None:
    import uuid

    from app.models.workspace import Workspace
    from app.services import alerts

    with db_session_factory() as db:
        ws = db.get(Workspace, uuid.UUID(shop[1]))
        assert alerts.rule_events(db, ws, date(2027, 7, 1)) == []  # a quiet stretch of the calendar
