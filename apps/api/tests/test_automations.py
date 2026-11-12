"""Automation agents: they run, are traced, only prepare drafts, and run on a daily schedule."""

import inspect
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.services.agents import automations
from tests.test_forecast_api import shop_csv
from tests.test_intelligence_api import make_shop

AUTOMATIONS = list(automations.NEW)


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "auto@shop.in", shop_csv(60))


def test_every_automation_is_listed(client: TestClient, shop) -> None:
    h, ws = shop
    listed = {
        w["key"]: w
        for w in client.get(f"/api/v1/workspaces/{ws}/agents/workflows", headers=h).json()
    }
    for key in AUTOMATIONS:
        assert listed[key]["automation"] is True


@pytest.mark.parametrize("workflow", AUTOMATIONS)
def test_each_automation_runs_to_a_conclusion_with_a_trace(
    client: TestClient, shop, workflow: str
) -> None:
    h, ws = shop
    r = client.post(
        f"/api/v1/workspaces/{ws}/agents/runs", json={"workflow": workflow}, headers=h
    ).json()
    assert r["status"] == "done", r.get("error")
    assert r["result"]["summary"]
    assert r["steps"]
    assert all(s["status"] in {"ok", "skipped"} for s in r["steps"]), r["steps"]


def test_udhaar_collector_drafts_reminders_and_reorder_planner_shares_lists(
    client: TestClient, shop
) -> None:
    h, ws = shop
    base = f"/api/v1/workspaces/{ws}"
    old = (date.today() - timedelta(days=75)).isoformat()
    client.post(
        f"{base}/udhaar/entries",
        json={"party": "Ramesh Yadav", "entry_date": old, "kind": "credit", "amount": 2100},
        headers=h,
    )
    r = client.post(
        f"{base}/agents/runs", json={"workflow": "udhaar_collector", "lang": "en"}, headers=h
    ).json()
    drafts = r["result"]["facts"]["drafts"]
    assert drafts[0]["name"] == "Ramesh Yadav"
    assert "2,100" in drafts[0]["text"]
    titles = " ".join(f["title"] for f in r["result"]["findings"])
    assert "not paid anything in over 60 days" in titles
    plan = client.post(
        f"{base}/agents/runs", json={"workflow": "reorder_planner"}, headers=h
    ).json()
    assert "order_lists" in plan["result"]["facts"] or plan["result"]["notes"]


def test_day_end_check_flags_a_short_drawer(client: TestClient, shop) -> None:
    h, ws = shop
    base = f"/api/v1/workspaces/{ws}"
    yday = (date.today() - timedelta(days=1)).isoformat()
    client.put(
        f"{base}/daily/close",
        json={"day": yday, "opening_cash": 1000, "cash_sales": 5000, "counted_cash": 5200},
        headers=h,
    )
    r = client.post(f"{base}/agents/runs", json={"workflow": "day_end_check"}, headers=h).json()
    titles = " ".join(f["title"] for f in r["result"]["findings"])
    assert "short by ₹800" in titles


def test_expiry_clearance_sorts_what_to_remove_and_what_to_sell(client: TestClient, shop) -> None:
    h, ws = shop
    base = f"/api/v1/workspaces/{ws}"
    for name, d in (("Curd", -2), ("Bread", 2)):
        client.post(
            f"{base}/daily/expiry",
            json={"name": name, "expires_on": (date.today() + timedelta(days=d)).isoformat()},
            headers=h,
        )
    r = client.post(f"{base}/agents/runs", json={"workflow": "expiry_clearance"}, headers=h).json()
    titles = [f["title"] for f in r["result"]["findings"]]
    assert titles == ["Take 1 expired items off the shelf", "Sell 1 items first this week"]


def test_automations_are_read_only() -> None:
    src = inspect.getsource(automations)
    for banned in (
        "db.add(",
        "db.delete(",
        ".commit(",
        "requests.",
        "httpx",
        "urllib",
        "subprocess",
        "open(",
        "smtp",
    ):
        assert banned not in src, banned


def test_schedule_runs_each_enabled_agent_once_a_day(
    client: TestClient, shop, db_session_factory
) -> None:
    from app.services.agents.schedule import run_due

    h, ws = shop
    base = f"/api/v1/workspaces/{ws}/agents/schedule"
    rows = client.get(base, headers=h).json()
    assert {r["workflow"] for r in rows} == set(AUTOMATIONS)
    assert all(r["enabled"] is False for r in rows)
    assert (
        client.put(
            base, json={"workflow": "morning_brief", "enabled": True, "hour": 7}, headers=h
        ).status_code
        == 200
    )
    assert (
        client.put(
            base, json={"workflow": "nope", "enabled": True, "hour": 7}, headers=h
        ).status_code
        == 400
    )
    early = datetime(2026, 11, 12, 0, 30, tzinfo=UTC)  # 06:00 in India: before 07:00
    late = datetime(2026, 11, 12, 3, 0, tzinfo=UTC)  # 08:30 in India
    with db_session_factory() as db:
        assert run_due(db, early) == []
        first = run_due(db, late)
        assert [r["workflow"] for r in first] == ["morning_brief"]
        assert run_due(db, late + timedelta(hours=2)) == []  # once per local day
    runs = client.get(f"/api/v1/workspaces/{ws}/agents/runs", headers=h).json()
    assert runs[0]["workflow"] == "morning_brief"


def test_only_admins_change_the_schedule(client: TestClient, shop, make_user) -> None:
    h, ws = shop
    viewer = make_user("v@shop.in")
    inv = client.post(
        f"/api/v1/workspaces/{ws}/invitations", json={"role": "viewer"}, headers=h
    ).json()
    client.post("/api/v1/invitations/accept", json={"token": inv["token"]}, headers=viewer)
    r = client.put(
        f"/api/v1/workspaces/{ws}/agents/schedule",
        json={"workflow": "morning_brief", "enabled": True},
        headers=viewer,
    )
    assert r.status_code == 403
