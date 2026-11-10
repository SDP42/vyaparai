# ruff: noqa: E501
"""Agent workflows: a planted sales drop is explained, failures and budgets are bounded, traces are stored."""

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.services.agents import engine, workflows
from tests.test_intelligence_api import make_shop
from tests.test_team import _join

START = date(2026, 8, 3)


def drop_csv() -> str:
    """Product B sells 10 a day for 30 days, then 2 a day; product A is steady. Net sales fall in the second month."""
    lines = [
        "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status"
    ]
    for i in range(60):
        d = (START + timedelta(days=i)).strftime("%d/%m/%Y")
        lines.append(f"A{i},{d},SKU-A,Steady Tea,Cat,5,100,0,60,C1,MH,Pune,Store,Paid")
        lines.append(
            f"B{i},{d},SKU-B,Fading Biscuit,Cat,{10 if i < 30 else 2},50,0,30,C2,MH,Pune,Store,Paid"
        )
    return "\n".join(lines) + "\n"


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "agent@shop.in", drop_csv())


def run(client, shop, **body):
    h, ws = shop
    return client.post(
        f"/api/v1/workspaces/{ws}/agents/runs",
        json={"workflow": "investigate_sales", **body},
        headers=h,
    )


def test_a_planted_drop_is_found_and_explained(client: TestClient, shop) -> None:
    to = START + timedelta(days=59)
    r = run(client, shop, date_from=(to - timedelta(days=29)).isoformat(), date_to=to.isoformat())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "done"
    res = d["result"]
    assert "fell" in res["summary"]
    titles = " ".join(f["title"] for f in res["findings"])
    assert "Fading Biscuit" in " ".join(e["label"] for f in res["findings"] for e in f["evidence"])
    assert "products fell" in titles
    assert res["caveat"]
    assert all(
        f["kind"] in {"measured", "context"} and 0 <= f["weight"] <= 1 for f in res["findings"]
    )
    steps = [s["node"] for s in d["steps"]]
    assert steps[:3] == ["scope", "headline", "drivers"]
    assert steps[-1] == "conclude"
    assert all(s["status"] == "ok" for s in d["steps"])


def test_a_flat_period_skips_the_deep_checks(client: TestClient, shop) -> None:
    # two halves of the first month are identical, so there is nothing to explain
    a = START + timedelta(days=1)
    r = run(
        client,
        shop,
        date_from=(a + timedelta(days=14)).isoformat(),
        date_to=(a + timedelta(days=28)).isoformat(),
    ).json()
    assert [s["node"] for s in r["steps"]] == ["scope", "headline", "conclude"]
    assert "no material change" in r["result"]["summary"]


def test_a_failing_node_is_retried_then_recorded_and_the_run_goes_on(
    client: TestClient, shop, monkeypatch
) -> None:
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise RuntimeError("cost service down")

    monkeypatch.setattr(workflows.alert_service, "rule_margin", boom)
    to = START + timedelta(days=59)
    d = run(
        client, shop, date_from=(to - timedelta(days=29)).isoformat(), date_to=to.isoformat()
    ).json()
    assert d["status"] == "done"
    cost = next(s for s in d["steps"] if s["node"] == "cost_check")
    assert cost["status"] == "failed"
    assert cost["attempts"] == engine.MAX_ATTEMPTS == calls["n"]
    assert "RuntimeError" in cost["error"]
    assert any("cost_check could not be checked" in n for n in d["result"]["notes"])
    assert d["steps"][-1]["node"] == "conclude"


def test_the_step_budget_stops_the_run_cleanly(client: TestClient, shop, monkeypatch) -> None:
    monkeypatch.setattr(engine, "MAX_NODES", 4)
    to = START + timedelta(days=59)
    d = run(
        client, shop, date_from=(to - timedelta(days=29)).isoformat(), date_to=to.isoformat()
    ).json()
    assert d["status"] == "done"
    skipped = [s for s in d["steps"] if s["status"] == "skipped"]
    assert skipped
    assert "step limit" in skipped[0]["error"]
    assert "stopped before it could conclude" in d["result"]["summary"]


def test_runs_are_listed_read_back_and_permissioned(client: TestClient, shop, make_user) -> None:
    h, ws = shop
    first = run(client, shop).json()
    base = f"/api/v1/workspaces/{ws}/agents"
    assert [r["id"] for r in client.get(f"{base}/runs", headers=h).json()] == [first["id"]]
    got = client.get(f"{base}/runs/{first['id']}", headers=h).json()
    assert got["steps"]
    assert got["steps"][0]["input"]["params"] == got["params"]
    assert {w["key"] for w in client.get(f"{base}/workflows", headers=h).json()} == {
        "investigate_sales",
        "weekly_review",
    }
    viewer = make_user("viewer@shop.in")
    _join(client, ws, h, viewer, "viewer")
    assert client.get(f"{base}/runs/{first['id']}", headers=viewer).status_code == 200
    assert (
        client.post(
            f"{base}/runs", json={"workflow": "investigate_sales"}, headers=viewer
        ).status_code
        == 403
    )
    stranger = make_user("s@s.in")
    assert client.get(f"{base}/runs/{first['id']}", headers=stranger).status_code == 404
    assert client.post(f"{base}/runs", json={"workflow": "nope"}, headers=h).status_code == 400


def test_the_workflow_is_read_only_and_offline() -> None:
    import inspect

    src = inspect.getsource(workflows)
    for banned in ("db.add(", "db.delete(", "requests.", "httpx", "urllib", "subprocess", "open("):
        assert banned not in src, banned
    for var in ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2", "LANGSMITH_API_KEY"):
        assert (
            os.environ.get(var, "").lower() not in {"true", "1"}
            if "TRACING" in var
            else not os.environ.get(var)
        )


def test_a_period_past_the_last_sale_is_trimmed_not_counted_as_zero(
    client: TestClient, shop
) -> None:
    last = START + timedelta(days=59)
    d = run(
        client,
        shop,
        date_from=(last - timedelta(days=9)).isoformat(),
        date_to=(last + timedelta(days=20)).isoformat(),
    ).json()
    assert d["result"]["facts"]["to"] == last.isoformat()
    assert any("trimmed" in n for n in d["result"]["notes"])
