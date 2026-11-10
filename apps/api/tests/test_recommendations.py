# ruff: noqa: E501
"""Recommendations: candidates carry honest impact ranges, ranking is explained, decisions are audited."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.services.recommend import candidates, service
from tests.test_team import _join

TODAY = date.today()


def d(n: int) -> str:
    return (TODAY - timedelta(days=n)).isoformat()


LEDGER = f"Date,Name,Phone,Type,Amount\n{d(70)},Big Debtor,,Credit,9000\n{d(65)},Another,,Credit,4000\n{d(5)},Fresh,,Credit,300\n".encode()


@pytest.fixture
def ws(client: TestClient, make_user):
    h = make_user("rec@shop.in")
    wid = client.post("/api/v1/workspaces", json={"name": "Shop"}, headers=h).json()["id"]
    return h, wid


def _ledger(client, h, wid, content: bytes = LEDGER):
    return client.post(
        f"/api/v1/workspaces/{wid}/udhaar/import", files={"file": ("l.csv", content)}, headers=h
    )


def _refresh(client, h, wid):
    return client.post(f"/api/v1/workspaces/{wid}/recommendations/refresh", headers=h).json()


def _list(client, h, wid, status="proposed"):
    return client.get(f"/api/v1/workspaces/{wid}/recommendations?status={status}", headers=h).json()


def test_score_rewards_impact_and_confidence_and_penalises_effort() -> None:
    base = {"impact": {"expected": 10000}, "confidence": "high", "effort": "S"}
    assert service.score(base) == 10000
    assert service.score({**base, "confidence": "low"}) < service.score(base)
    assert (
        service.score({**base, "effort": "L"})
        < service.score({**base, "effort": "M"})
        < service.score(base)
    )
    assert service.score({**base, "impact": {"expected": None}}) == 0.0


def test_udhaar_recommendation_states_its_range_and_that_it_is_an_assumption(
    client: TestClient, ws
) -> None:
    h, wid = ws
    _ledger(client, h, wid)
    r = _refresh(client, h, wid)
    assert r["found"] == 1
    rec = _list(client, h, wid)[0]
    assert rec["kind"] == "collect_udhaar"
    assert "13,000" in rec["title"]
    i = rec["impact"]
    assert i["low"] < i["expected"] < i["high"]
    assert i["low"] == round(13000 * 0.3)
    assert i["measured"] is False
    assert any("unmeasured" in a for a in i["assumptions"])
    assert {e["label"] for e in rec["evidence"]} >= {"Big Debtor", "Another"}
    assert rec["link"] == "/app/udhaar"
    assert (
        client.get(f"/api/v1/workspaces/{wid}/recommendations/summary", headers=h).json()[
            "proposed_impact"
        ]["expected"]
        == i["expected"]
    )


def test_margin_leak_candidate_uses_the_measured_leak_and_a_range(monkeypatch) -> None:
    leak = {
        "key": "margin_leak|X",
        "title": "Atta: cost up 10% but the price did not follow",
        "detail": "Margin fell.",
        "evidence": {
            "cost_change_pct": 10.0,
            "price_change_pct": 0.0,
            "margin_prev_pct": 20.0,
            "margin_now_pct": 12.0,
            "leak_amount": 2000.0,
            "suggested_price": 55.0,
        },
    }
    monkeypatch.setattr(candidates.alert_service, "rule_margin", lambda *a, **k: ([leak], None))
    from types import SimpleNamespace
    from uuid import uuid4

    c = candidates.margin_leaks(None, SimpleNamespace(id=uuid4()), TODAY)[0]  # type: ignore[arg-type]
    assert c["impact"]["measured"] is True
    assert (c["impact"]["low"], c["impact"]["expected"], c["impact"]["high"]) == (1000, 1600, 2000)
    assert "₹55" in c["title"]


def test_decisions_follow_the_lifecycle_and_are_remembered(client: TestClient, ws) -> None:
    h, wid = ws
    _ledger(client, h, wid)
    _refresh(client, h, wid)
    rec = _list(client, h, wid)[0]
    base = f"/api/v1/workspaces/{wid}/recommendations/{rec['id']}"
    a = client.post(
        f"{base}/approve", json={"note": "I will message them Monday"}, headers=h
    ).json()
    assert a["status"] == "approved"
    assert a["note"] == "I will message them Monday"
    assert client.post(f"{base}/approve", headers=h).status_code == 400  # already approved
    assert client.post(f"{base}/done", headers=h).json()["status"] == "done"
    assert client.post(f"{base}/reopen", headers=h).json()["status"] == "proposed"
    assert client.post(f"{base}/dismiss", headers=h).json()["status"] == "dismissed"
    _refresh(client, h, wid)
    assert (
        _list(client, h, wid) == []
    )  # a dismissed item is not proposed again while the cause remains
    assert _list(client, h, wid, "dismissed")[0]["id"] == rec["id"]
    logs = client.get(f"/api/v1/workspaces/{wid}/audit-logs", headers=h).json()["items"]
    assert {"recommendation.approve", "recommendation.done", "recommendation.dismiss"} <= {
        x["action"] for x in logs
    }


def test_an_item_whose_cause_is_gone_becomes_stale(client: TestClient, ws) -> None:
    h, wid = ws
    _ledger(client, h, wid)
    _refresh(client, h, wid)
    rec = _list(client, h, wid)[0]
    client.post(f"/api/v1/workspaces/{wid}/recommendations/{rec['id']}/approve", headers=h)
    settle = f"Date,Name,Type,Amount\n{d(1)},Big Debtor,Payment,9000\n{d(1)},Another,Payment,4000\n".encode()
    _ledger(client, h, wid, settle)
    r = _refresh(client, h, wid)
    assert r["stale"] == 1
    assert _list(client, h, wid, "stale")[0]["id"] == rec["id"]


def test_one_broken_signal_does_not_hide_the_others_or_stale_existing_items(
    client: TestClient, ws, monkeypatch
) -> None:
    h, wid = ws
    _ledger(client, h, wid)
    _refresh(client, h, wid)

    def boom(*a, **k):
        raise RuntimeError("signal down")

    monkeypatch.setattr(candidates, "GENERATORS", [candidates.reorder, boom, candidates.udhaar])
    r = _refresh(client, h, wid)
    assert r["errors"]
    assert r["stale"] == 0
    assert len(_list(client, h, wid)) == 1


def test_only_analysts_decide_and_strangers_see_nothing(client: TestClient, ws, make_user) -> None:
    h, wid = ws
    _ledger(client, h, wid)
    _refresh(client, h, wid)
    rec = _list(client, h, wid)[0]
    viewer = make_user("v@shop.in")
    _join(client, wid, h, viewer, "viewer")
    base = f"/api/v1/workspaces/{wid}/recommendations"
    assert client.get(base, headers=viewer).status_code == 200
    assert client.post(f"{base}/{rec['id']}/approve", headers=viewer).status_code == 403
    assert client.post(f"{base}/refresh", headers=viewer).status_code == 403
    stranger = make_user("s@s.in")
    assert client.get(base, headers=stranger).status_code == 404


def test_weekly_review_workflow_lists_the_top_suggestions(client: TestClient, ws) -> None:
    h, wid = ws
    _ledger(client, h, wid)
    r = client.post(
        f"/api/v1/workspaces/{wid}/agents/runs", json={"workflow": "weekly_review"}, headers=h
    ).json()
    assert r["status"] == "done"
    assert [s["node"] for s in r["steps"]] == ["refresh", "alerts", "rank", "conclude"]
    assert "things to do this week" in r["result"]["summary"]
    assert "estimates" in r["result"]["caveat"]
