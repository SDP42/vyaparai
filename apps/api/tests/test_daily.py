"""Daily routines: expenses, galla tally, expiry, supplier order lists, quick entries, Today."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.services import daily
from tests.test_forecast_api import shop_csv
from tests.test_intelligence_api import make_shop

Make = object


@pytest.mark.parametrize(
    ("text", "kind", "who", "amount"),
    [
        ("Ramesh ko 200 udhaar", "credit", "Ramesh", 200),
        ("Sunita Patil ko paanch sau udhaar diya", "credit", "Sunita Patil", 500),
        ("Ramesh ne 500 diye", "payment", "Ramesh", 500),
        ("रमेश को दो सौ उधार", "credit", "रमेश", 200),
        ("रमेश ने पाँच सौ दिए", "payment", "रमेश", 500),
    ],
)
def test_parse_udhaar_sentences(text: str, kind: str, who: str, amount: int) -> None:
    out = daily.parse_entry(text)
    assert out["understood"] is True
    assert out["kind"] == kind
    assert out["party"] == who
    assert out["amount"] == amount


@pytest.mark.parametrize(
    ("text", "cat", "amount"),
    [
        ("chai 60 kharcha", "tea", 60),
        ("bijli ka bill 1200 kharcha", "electricity", 1200),
        ("auto bhada 150 kharcha", "transport", 150),
        ("खर्च 300", "other", 300),
    ],
)
def test_parse_expenses(text: str, cat: str, amount: int) -> None:
    out = daily.parse_entry(text)
    assert out["kind"] == "expense"
    assert out["category"] == cat
    assert out["amount"] == amount


@pytest.mark.parametrize(
    ("text", "reason"),
    [("Ramesh ko udhaar", "no_amount"), ("aaj 500", "no_kind"), ("ko 500 udhaar", "no_name")],
)
def test_unclear_sentences_are_not_guessed(text: str, reason: str) -> None:
    out = daily.parse_entry(text)
    assert out["understood"] is False
    assert out["reason"] == reason


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "d@shop.in", shop_csv(60))


def test_expenses_and_galla_close(client: TestClient, shop) -> None:
    h, ws = shop
    base = f"/api/v1/workspaces/{ws}/daily"
    day = "2026-09-30"
    assert (
        client.post(
            f"{base}/expenses", json={"spent_on": day, "category": "tea", "amount": 60}, headers=h
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"{base}/expenses",
            json={"spent_on": day, "category": "rent", "amount": 5000, "paid_by": "bank"},
            headers=h,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"{base}/expenses", json={"spent_on": day, "category": "bogus", "amount": 5}, headers=h
        ).status_code
        == 400
    )
    ex = client.get(f"{base}/expenses?from=2026-09-01&to=2026-09-30", headers=h).json()
    assert Decimal(str(ex["total"])) == Decimal("5060")
    assert ex["by_category"][0]["category"] == "rent"
    # udhaar paid back in cash that day counts towards the drawer
    client.post(
        f"/api/v1/workspaces/{ws}/udhaar/entries",
        json={"party": "Ramesh", "entry_date": day, "kind": "payment", "amount": 200},
        headers=h,
    )
    view = client.get(f"{base}/close?day={day}", headers=h).json()
    assert Decimal(str(view["cash_expenses"])) == Decimal("60")
    assert view["file_sales"] is not None  # the sample file has this day
    r = client.put(
        f"{base}/close",
        json={
            "day": day,
            "opening_cash": 2000,
            "cash_sales": 3000,
            "upi_sales": 1500,
            "card_sales": 0,
            "taken_out": 1000,
            "counted_cash": 4100,
        },
        headers=h,
    ).json()
    s = r["saved"]
    received = Decimal(str(r["udhaar_received"]))
    # expected = 2000 + 3000 + received - 60 - 1000
    assert Decimal(str(s["expected_cash"])) == Decimal("3940") + received
    assert Decimal(str(s["difference"])) == Decimal("4100") - Decimal(str(s["expected_cash"]))
    assert s["status"] in {"matches", "short", "extra"}
    assert Decimal(str(s["typed_sales"])) == Decimal("4500")
    hist = client.get(f"{base}/close/history", headers=h).json()
    assert hist[0]["day"] == day


def test_expiry_watch_buckets_and_clearing(client: TestClient, shop) -> None:
    h, ws = shop
    base = f"/api/v1/workspaces/{ws}/daily/expiry"
    today = date.today()
    for name, days in (("Curd 400g", -1), ("Bread", 3), ("Biscuits", 20), ("Ghee 1L", 120)):
        assert (
            client.post(
                base,
                json={"name": name, "expires_on": (today + timedelta(days=days)).isoformat()},
                headers=h,
            ).status_code
            == 201
        )
    out = client.get(base, headers=h).json()
    assert out["counts"] == {"expired": 1, "this_week": 1, "this_month": 1, "later": 1}
    first = out["items"][0]
    assert first["name"] == "Curd 400g"
    assert (
        client.post(f"{base}/{first['id']}/clear", json={"how": "thrown"}, headers=h).status_code
        == 204
    )
    assert client.get(base, headers=h).json()["counts"]["expired"] == 0
    assert (
        client.post(f"{base}/{first['id']}/clear", json={"how": "eaten"}, headers=h).status_code
        == 400
    )


def test_quick_save_creates_udhaar_and_expense(client: TestClient, shop) -> None:
    h, ws = shop
    base = f"/api/v1/workspaces/{ws}/daily/quick"
    p = client.post(f"{base}/parse", json={"text": "Ramesh ko 250 udhaar"}, headers=h).json()
    saved = client.post(
        f"{base}/save",
        json={"kind": p["kind"], "party": p["party"], "amount": p["amount"]},
        headers=h,
    )
    assert saved.status_code == 201
    assert saved.json()["saved"] == "credit"
    parties = client.get(f"/api/v1/workspaces/{ws}/udhaar/parties", headers=h).json()
    names = [x["name"] for x in (parties["items"] if isinstance(parties, dict) else parties)]
    assert "Ramesh" in names
    e = client.post(
        f"{base}/save", json={"kind": "expense", "category": "tea", "amount": 40}, headers=h
    )
    assert e.json()["saved"] == "expense"


def test_order_lists_are_text_to_share(client: TestClient, shop) -> None:
    h, ws = shop
    out = client.get(f"/api/v1/workspaces/{ws}/daily/orders?lang=en", headers=h).json()
    assert "groups" in out
    for g in out["groups"]:
        assert g["text"].startswith("Hello")
        assert g["share_url"].startswith("https://wa.me/?text=")


def test_today_has_sales_and_respects_persona(client: TestClient, shop, make_user) -> None:
    h, ws = shop
    out = client.get(f"/api/v1/workspaces/{ws}/daily/today", headers=h).json()
    assert out["sales"]["net"] is not None
    assert {"order", "expiry", "cash"} <= set(out)
    staff = make_user("c@shop.in")
    inv = client.post(
        f"/api/v1/workspaces/{ws}/invitations",
        json={"role": "viewer", "persona": "cashier"},
        headers=h,
    ).json()
    client.post("/api/v1/invitations/accept", json={"token": inv["token"]}, headers=staff)
    mine = client.get(f"/api/v1/workspaces/{ws}/daily/today", headers=staff).json()
    assert "cash" not in mine and "udhaar" not in mine  # counter staff: no galla, no credit book
    assert "order" in mine
    assert client.get(f"/api/v1/workspaces/{ws}/daily/close", headers=staff).status_code == 403
    assert client.get(f"/api/v1/workspaces/{ws}/daily/expiry", headers=staff).status_code == 200


def test_viewer_cannot_write_the_galla(client: TestClient, shop, make_user) -> None:
    h, ws = shop
    acct = make_user("a@shop.in")
    inv = client.post(
        f"/api/v1/workspaces/{ws}/invitations",
        json={"role": "viewer", "persona": "accountant"},
        headers=h,
    ).json()
    client.post("/api/v1/invitations/accept", json={"token": inv["token"]}, headers=acct)
    base = f"/api/v1/workspaces/{ws}/daily"
    assert client.get(f"{base}/close", headers=acct).status_code == 200
    assert (
        client.put(
            f"{base}/close", json={"day": "2026-09-30", "counted_cash": 10}, headers=acct
        ).status_code
        == 403
    )
