"""Udhaar: FIFO ageing, import in several layouts, reminders, the alert, and access."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.services import credit

D = Decimal
TODAY = date.today()


def d(days_ago: int) -> date:
    return TODAY - timedelta(days=days_ago)


# ------------------------------------------------------------------ pure logic


def test_payments_settle_the_oldest_credit_first() -> None:
    credits = [(d(100), D(500)), (d(40), D(300)), (d(5), D(200))]
    pieces, advance = credit.settle(credits, [(d(10), D(600))])
    assert [(o.date, o.amount) for o in pieces] == [(d(40), D(200)), (d(5), D(200))]
    assert advance == 0


def test_overpayment_is_an_advance_not_negative_owed() -> None:
    pieces, advance = credit.settle([(d(10), D(100))], [(d(1), D(250))])
    assert pieces == []
    assert advance == D(150)


def test_phone_and_name_cleaning() -> None:
    assert credit.clean_phone("98765 43210") == "919876543210"
    assert credit.clean_phone("+91-98765-43210") == "919876543210"
    assert credit.clean_phone("123") is None
    assert credit.party_key("  Ramesh   Sharma. ") == "ramesh sharma"


def test_reminder_tone_gets_firmer_with_age_and_follows_language() -> None:
    base = {"name": "Ramesh Sharma", "owed": D(1200)}
    young = credit.draft({**base, "oldest_days": 12}, "Kulkarni Stores", "en")
    old = credit.draft({**base, "oldest_days": 75}, "Kulkarni Stores", "en")
    assert "small reminder" in young
    assert "cannot give more credit" in old
    assert "₹1,200" in young
    assert "Ramesh" in young
    assert "udhaar nahi" in credit.draft({**base, "oldest_days": 75}, "Kulkarni Stores", "hinglish")
    assert "उधार" in credit.draft({**base, "oldest_days": 75}, "Kulkarni Stores", "hi")


# ------------------------------------------------------------------ API


@pytest.fixture
def ws(client: TestClient, make_user):
    h = make_user("udhaar@shop.in")
    wid = client.post("/api/v1/workspaces", json={"name": "Kulkarni Stores"}, headers=h).json()[
        "id"
    ]
    return h, wid


def _csv(rows: list[str], header: str = "Date,Name,Phone,Type,Amount,Note") -> bytes:
    return ("\n".join([header, *rows]) + "\n").encode()


def _imp(client, h, wid, content: bytes):
    return client.post(
        f"/api/v1/workspaces/{wid}/udhaar/import", files={"file": ("l.csv", content)}, headers=h
    )


LEDGER = [
    f"{d(95).isoformat()},Ramesh Sharma,9876543210,Credit,1000,groceries",
    f"{d(80).isoformat()},Ramesh Sharma,9876543210,Payment,400,upi",
    f"{d(50).isoformat()},Sunita Devi,,Credit,2500,monthly",
    f"{d(10).isoformat()},Sunita Devi,,Payment,500,cash",
    f"{d(20).isoformat()},Mohan Tea Stall,9123456780,Credit,8000,tea and snacks",
    f"{d(3).isoformat()},Fresh Person,,Credit,300,x",
]


def test_import_summary_ageing_and_priorities(client: TestClient, ws) -> None:
    h, wid = ws
    r = _imp(client, h, wid, _csv(LEDGER)).json()
    assert r["added"] == 6
    assert _imp(client, h, wid, _csv(LEDGER)).json()["added"] == 0  # idempotent
    base = f"/api/v1/workspaces/{wid}/udhaar"
    s = client.get(f"{base}/summary", headers=h).json()
    # Ramesh owes 600 (95 days), Sunita 2000 (50 days), Mohan 8000 (20 days), Fresh 300 (3 days)
    assert s["outstanding"] == "10900.00"
    assert s["parties_owing"] == 4
    assert s["buckets"]["90+"] == "600.00"
    assert s["buckets"]["31-60"] == "2000.00"
    assert s["buckets"]["0-30"] == "8300.00"
    assert s["overdue"] == "2600.00"
    ps = client.get(f"{base}/parties", headers=h).json()
    assert ps[0]["name"] in {
        "Mohan Tea Stall",
        "Sunita Devi",
    }  # amount x age decides, not amount alone
    ramesh = next(p for p in ps if p["name"] == "Ramesh Sharma")
    assert ramesh["behaviour"] == "stalled"
    assert ramesh["owed"] == "600.00"


def test_two_column_layout_and_negative_amounts_are_understood(client: TestClient, ws) -> None:
    h, wid = ws
    rows = [f"{d(30).isoformat()},Anita,5000,0", f"{d(5).isoformat()},Anita,0,2000"]
    r = _imp(client, h, wid, _csv(rows, "Date,Party Name,Credit,Payment")).json()
    assert r["added"] == 2
    p = client.get(f"/api/v1/workspaces/{wid}/udhaar/parties", headers=h).json()
    assert p[0]["owed"] == "3000.00"


def test_bad_files_and_rows_are_reported(client: TestClient, ws) -> None:
    h, wid = ws
    assert _imp(client, h, wid, b"Foo,Bar\n1,2\n").status_code == 422
    r = _imp(
        client,
        h,
        wid,
        _csv(
            [
                f"{d(3).isoformat()},Good,,Credit,100,",
                "not a date,Bad,,Credit,100,",
                f"{d(2).isoformat()},NoAmount,,Credit,,",
            ]
        ),
    ).json()
    assert r["added"] == 1
    assert r["rejected_count"] == 2


def test_reminders_have_whatsapp_links_only_with_a_phone(client: TestClient, ws) -> None:
    h, wid = ws
    _imp(client, h, wid, _csv(LEDGER))
    rem = client.get(f"/api/v1/workspaces/{wid}/udhaar/reminders?lang=en", headers=h).json()
    names = {r["name"]: r for r in rem}
    assert "Fresh Person" not in names  # under a week old: too early to chase
    assert names["Ramesh Sharma"]["whatsapp"].startswith("https://wa.me/919876543210?text=")
    assert names["Sunita Devi"]["whatsapp"] is None
    assert "Sunita" in names["Sunita Devi"]["message"]


def test_manual_entry_and_ledger_view(client: TestClient, ws) -> None:
    h, wid = ws
    base = f"/api/v1/workspaces/{wid}/udhaar"
    assert (
        client.post(
            f"{base}/entries",
            json={"party": "Geeta", "kind": "credit", "amount": "750.50"},
            headers=h,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"{base}/entries",
            json={"party": "Geeta", "kind": "credit", "amount": "750.50"},
            headers=h,
        ).status_code
        == 400
    )  # same entry twice today
    assert (
        client.post(
            f"{base}/entries", json={"party": "Geeta", "kind": "payment", "amount": "50"}, headers=h
        ).status_code
        == 201
    )
    led = client.get(f"{base}/parties/geeta", headers=h).json()
    assert led["owed"] == "700.50"
    assert len(led["entries"]) == 2
    assert (
        client.post(
            f"{base}/entries", json={"party": "X", "kind": "loan", "amount": "5"}, headers=h
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"{base}/entries", json={"party": "X", "kind": "credit", "amount": "-5"}, headers=h
        ).status_code
        == 422
    )


def test_overdue_credit_raises_an_alert_and_the_assistant_answers(client: TestClient, ws) -> None:
    h, wid = ws
    rows = [
        f"{d(70).isoformat()},Big Debtor,,Credit,9000,",
        f"{d(65).isoformat()},Another,,Credit,4000,",
    ]
    _imp(client, h, wid, _csv(rows))
    # a tiny sales file so alerts have a data range
    from tests.test_ingestion import full_flow

    sales = "Bill No,Bill Date,Item Code,Item Name,Qty,Rate\n" + "\n".join(
        f"B{i},{d(i).strftime('%d/%m/%Y')},SKU-A,Tea,2,100" for i in range(10)
    )
    _, b, _ = full_flow(client, h, wid, sales.encode())
    client.post(f"{b}/import", headers=h)
    alerts = client.get(f"/api/v1/workspaces/{wid}/alerts", headers=h).json()
    hit = [a for a in alerts["items"] if a["rule"] == "udhaar_overdue"]
    assert hit
    assert "₹13,000" in hit[0]["title"]
    a = client.post(
        f"/api/v1/workspaces/{wid}/assistant/ask", json={"question": "who owes me money"}, headers=h
    ).json()
    assert a["intent"] == "udhaar"
    assert "₹13,000" in a["answer"]


def test_viewers_see_balances_but_cannot_change_or_draft(client: TestClient, ws, make_user) -> None:
    from tests.test_team import _join

    h, wid = ws
    _imp(client, h, wid, _csv(LEDGER))
    viewer = make_user("v@shop.in")
    _join(client, wid, h, viewer, "viewer")
    base = f"/api/v1/workspaces/{wid}/udhaar"
    assert client.get(f"{base}/summary", headers=viewer).status_code == 200
    assert (
        client.post(
            f"{base}/entries", json={"party": "A", "kind": "credit", "amount": "5"}, headers=viewer
        ).status_code
        == 403
    )
    assert client.get(f"{base}/reminders", headers=viewer).status_code == 403
    stranger = make_user("s@s.in")
    assert client.get(f"{base}/summary", headers=stranger).status_code == 404
