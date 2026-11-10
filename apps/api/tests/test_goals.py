# ruff: noqa: E501
"""Goals on planted data: pace, projection ranges, status, rate and ceiling goals, and benchmarks from history."""

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models.workspace import Workspace
from app.services import goals
from tests.test_intelligence_api import make_shop
from tests.test_team import _join

HEAD = "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status\n"
START = date(2026, 7, 1)
END = date(2026, 10, 31)


def csv_text(noisy: bool = False) -> str:
    rows = []
    d = START
    i = 0
    while d <= END:
        qty = (8 if d.day % 2 == 0 else 12) if noisy else 10  # 800 / 1200 a day, or a steady 1000
        rows.append(
            f"B{i},{d.strftime('%d/%m/%Y')},SKU,Tea,Cat,{qty},100,0,60,C1,MH,Pune,Store,Paid"
        )
        d += timedelta(days=1)
        i += 1
    return HEAD + "\n".join(rows) + "\n"


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "goal@shop.in", csv_text())


def base(shop) -> str:
    return f"/api/v1/workspaces/{shop[1]}/goals"


def _create(client, shop, **kw):
    body = {
        "metric": "net_sales",
        "target": 30000,
        "period": "custom",
        "date_from": "2026-10-01",
        "date_to": "2026-10-31",
        **kw,
    }
    return client.post(base(shop), json=body, headers=shop[0])


# ------------------------------------------------------------------ finished periods


def test_a_finished_period_is_met_or_missed_against_the_real_number(
    client: TestClient, shop
) -> None:
    met = _create(client, shop, target=30000).json()
    assert met["status"] == "met"
    assert met["value"] == 31000
    assert met["progress_pct"] == pytest.approx(103.3, abs=0.1)
    missed = _create(client, shop, target=40000).json()
    assert missed["status"] == "missed"
    assert missed["needed_per_day"] is None  # nothing left to do


def test_rate_goals_compare_the_measure_as_it_stands(client: TestClient, shop) -> None:
    ok = _create(client, shop, metric="gross_margin", target=30).json()
    assert ok["status"] == "met"
    assert ok["value"] == pytest.approx(40, abs=0.1)
    assert _create(client, shop, metric="gross_margin", target=45).json()["status"] == "missed"
    assert (
        _create(client, shop, metric="discount_rate", target=5).json()["status"] == "met"
    )  # a ceiling: no discount at all
    assert _create(client, shop, metric="discount_rate", target=5).json()["direction"] == "at_most"


def test_a_ceiling_on_udhaar_uses_todays_ledger(client: TestClient, shop) -> None:
    h = shop[0]
    today = date.today()
    ledger = f"Date,Name,Type,Amount\n{(today - timedelta(days=70)).isoformat()},Big,Credit,13000\n".encode()
    client.post(
        f"/api/v1/workspaces/{shop[1]}/udhaar/import", files={"file": ("l.csv", ledger)}, headers=h
    )
    g = client.post(
        base(shop),
        json={
            "metric": "udhaar_overdue",
            "target": 5000,
            "period": "custom",
            "date_from": (today - timedelta(days=5)).isoformat(),
            "date_to": (today + timedelta(days=5)).isoformat(),
        },
        headers=h,
    ).json()
    assert g["status"] == "behind"
    assert g["value"] == 13000


# ------------------------------------------------------------------ in the middle of a period (clock controlled)


def _goal(db: Session, ws: uuid.UUID, user: uuid.UUID, target: float, metric: str = "net_sales"):
    workspace = db.get(Workspace, ws)
    assert workspace is not None
    g = goals.create(
        db,
        workspace,
        user,
        name="Oct",
        metric=metric,
        target=target,
        period="custom",
        start=date(2026, 10, 1),
        end=date(2026, 10, 31),
        today=date(2026, 10, 16),
    )
    return workspace, g


def test_pace_projection_and_status_in_the_middle_of_the_month(
    client: TestClient, shop, db_session_factory: sessionmaker[Session]
) -> None:
    ws = uuid.UUID(shop[1])
    me = uuid.UUID(client.get("/api/v1/auth/me", headers=shop[0]).json()["id"])
    today = date(2026, 10, 16)
    with db_session_factory() as db:
        w, g = _goal(db, ws, me, 31000)
        p = goals.progress(db, w, g, today)
        assert p["value"] == 16000  # 1 to 16 October at 1,000 a day
        assert p["elapsed_days"] == 16
        assert p["pace"] == pytest.approx(1.0, abs=0.01)
        assert p["projection"]["expected"] == pytest.approx(31000)
        assert p["needed_per_day"] == pytest.approx(1000)
        assert p["status"] == "on_track"  # steady sales: the whole range reaches it
        _, far = _goal(db, ws, me, 45000)
        assert goals.progress(db, w, far, today)["status"] == "behind"
        _, low = _goal(db, ws, me, 15000)
        assert goals.progress(db, w, low, today)["status"] == "achieved"


def test_uncertain_finishes_are_at_risk_not_promised(
    client: TestClient, make_user, db_session_factory: sessionmaker[Session]
) -> None:
    h = make_user("noisy@shop.in")
    ws = make_shop(client, make_user, "noisy2@shop.in", csv_text(noisy=True))[1]
    me = uuid.UUID(client.get("/api/v1/auth/me", headers=make_user("x@y.in")).json()["id"])
    _ = h
    with db_session_factory() as db:
        w, g = _goal(db, uuid.UUID(ws), me, 31000)
        p = goals.progress(db, w, g, date(2026, 10, 16))
        proj = p["projection"]
        assert proj["low"] < proj["expected"] < proj["high"]
        assert p["status"] == "at_risk"  # the target sits inside the likely range


# ------------------------------------------------------------------ benchmarks from the shop's own history


def test_benchmarks_come_from_past_periods_of_the_same_length(client: TestClient, shop) -> None:
    b = client.get(f"{base(shop)}/benchmarks?metric=net_sales&period=month", headers=shop[0]).json()
    assert b["enough"] is True
    assert [p["from"] for p in b["periods"]][:2] == ["2026-10-01", "2026-09-01"]
    assert b["median"] == 31000
    assert b["best"] == 31000
    assert b["stretch"] >= b["median"]
    assert "last 4 months" in b["note"]
    assert "peer" not in str(b).lower()


def test_too_little_history_is_said_plainly(client: TestClient, make_user) -> None:
    h = make_user("short@shop.in")
    short = (
        HEAD
        + "\n".join(
            f"B{i},{(date(2026, 9, 1) + timedelta(days=i)).strftime('%d/%m/%Y')},SKU,Tea,Cat,10,100,0,60,C1,MH,Pune,Store,Paid"
            for i in range(45)
        )
        + "\n"
    )
    shop2 = make_shop(client, lambda *_: h, "unused", short)
    b = client.get(f"/api/v1/workspaces/{shop2[1]}/goals/benchmarks", headers=h).json()
    assert b["enough"] is False
    assert "Not enough history" in b["note"]


# ------------------------------------------------------------------ validation and access


def test_validation_listing_closing_and_permissions(client: TestClient, shop, make_user) -> None:
    h, ws = shop
    assert _create(client, shop, metric="nope").status_code == 400
    assert (
        client.post(
            base(shop), json={"metric": "net_sales", "target": 0, "period": "month"}, headers=h
        ).status_code
        == 422
    )
    assert (
        client.post(
            base(shop), json={"metric": "net_sales", "target": 5, "period": "custom"}, headers=h
        ).status_code
        == 400
    )
    a, b = _create(client, shop, target=40000).json(), _create(client, shop, target=30000).json()
    listed = client.get(base(shop), headers=h).json()
    assert [g["status"] for g in listed] == ["missed", "met"]  # trouble first
    assert client.delete(f"{base(shop)}/{a['id']}", headers=h).status_code == 204
    assert [g["id"] for g in client.get(base(shop), headers=h).json()] == [b["id"]]
    viewer, stranger = make_user("v@shop.in"), make_user("s@s.in")
    _join(client, ws, h, viewer, "viewer")
    assert client.get(base(shop), headers=viewer).status_code == 200
    assert (
        client.post(
            base(shop), json={"metric": "net_sales", "target": 5, "period": "month"}, headers=viewer
        ).status_code
        == 403
    )
    assert client.get(base(shop), headers=stranger).status_code == 404
    assert any(
        m["key"] == "net_sales" for m in client.get(f"{base(shop)}/metrics", headers=h).json()
    )
