# ruff: noqa: E501
"""Owner digest checked against a shop whose numbers are known by hand.

A sells 10 units a day (rate 100, cost 60) on 5-18 Oct and 12 a day on 19-25 Oct; walk-in bills.
On Sun 25 Oct a second bill sells 5 units of B (rate 40, cost 30). Customers R1-R3 bought on 3 and
10 Aug and not since, so they are lapsed regulars.

Daily (Sun 25 Oct vs Sun 18 Oct): sales 1400 vs 1000 = +40.0 %; orders 2 vs 1 = +100.0 %;
margin (1200*0.4 + 200*0.25)/1400 = 37.86 -> 37.9 % vs 40.0 -> down 2.1 pts.
Weekly (19-25 Oct vs 12-18 Oct): sales 8600 vs 7000 = +22.9 %; orders 8 vs 7 = +14.3 %;
margin 3410/8600 = 39.65 -> 39.7 % vs 40.0 -> down 0.4 pts.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.services import digest, digest_delivery, mailer
from tests.test_intelligence_api import make_shop

HEAD = "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status"


def shop_csv() -> str:
    lines = [HEAD]
    for r in ("R1", "R2", "R3"):
        for day in ("03/08/2026", "10/08/2026"):
            lines.append(f"{r}-{day},{day},SKU-A,Atta,Cat,1,100,0,60,{r},MH,Pune,Store,Paid")
    d = date(2026, 10, 5)
    while d <= date(2026, 10, 25):
        qty = 12 if d >= date(2026, 10, 19) else 10
        lines.append(f"A{d:%m%d},{d:%d/%m/%Y},SKU-A,Atta,Cat,{qty},100,0,60,,,,Store,Paid")
        d += timedelta(days=1)
    lines.append("B1025,25/10/2026,SKU-B,Salt,Cat,5,40,0,30,,,,Store,Paid")
    return "\n".join(lines) + "\n"


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "dg@shop.in", shop_csv())


def url(shop, path: str) -> str:
    return f"/api/v1/workspaces/{shop[1]}/digests{path}"


# ---------------------------------------------------------------- pure rules


def test_rupee_formatting_uses_indian_grouping() -> None:
    assert digest.inr(999) == "₹999"
    assert digest.inr(1400) == "₹1,400"
    assert digest.inr(100000) == "₹1,00,000"
    assert digest.inr(1234567) == "₹12,34,567"
    assert digest.inr(Decimal("1399.5")) == "₹1,400"
    assert digest.inr(-2500) == "-₹2,500"


def ctx(**kw):
    base = {
        "lapsed_regulars": 0,
        "risers": [],
        "fallers": [],
        "cost_coverage": Decimal(100),
        "sales_change_pct": Decimal(0),
        "kind": "daily",
    }
    return digest.ActionContext(**{**base, **kw})


def test_actions_are_prioritised_and_thresholded() -> None:
    assert digest.choose_actions(ctx())[0]["kind"] == "steady"
    assert (
        digest.choose_actions(ctx(lapsed_regulars=2))[0]["kind"] == "steady"
    )  # below the threshold
    first = digest.choose_actions(ctx(lapsed_regulars=3))[0]
    assert first["kind"] == "winback"
    assert "Message 3 regular customers" in first["title"]
    riser = {"name": "Atta", "units_last": 100, "units_next": 130, "change_pct": 30.0}
    small = {
        "name": "Salt",
        "units_last": 4,
        "units_next": 8,
        "change_pct": 100.0,
    }  # too small to trust
    assert digest.choose_actions(ctx(risers=[small]))[0]["kind"] == "steady"
    acts = digest.choose_actions(
        ctx(
            lapsed_regulars=5,
            risers=[riser],
            sales_change_pct=Decimal(-15),
            cost_coverage=Decimal(40),
        )
    )
    assert [a["kind"] for a in acts] == ["winback", "stock_up", "sales_drop", "add_costs"]
    falling = {"name": "Oil", "units_last": 50, "units_next": 30, "change_pct": -40.0}
    assert digest.choose_actions(ctx(fallers=[falling]))[0]["kind"] == "ease_off"


# ---------------------------------------------------------------- API


def test_daily_digest_matches_hand_computed_numbers(client: TestClient, shop) -> None:
    d = client.get(url(shop, "/preview"), params={"kind": "daily"}, headers=shop[0]).json()
    assert d["as_of"] == "2026-10-25"
    by = {h["key"]: h for h in d["headline"]}
    assert by["net_sales"]["value"] == "₹1,400"
    assert by["net_sales"]["change"] == "40.0"
    assert by["orders"]["value"] == "2"
    assert by["orders"]["change"] == "100.0"
    assert by["gross_margin"]["value"] == "37.9%"
    assert by["gross_margin"]["change"] == "-2.1"
    assert "Sales: ₹1,400 (▲ 40.0% vs last Sun)" in d["text"]
    assert "Margin: 37.9% (▼ 2.1 pts vs last Sun)" in d["text"]
    assert d["versus"] == "vs last Sun"
    assert d["action"]["kind"] == "winback"  # R1-R3 are lapsed regulars
    assert "Message 3 regular customers" in d["text"]
    assert "/app/campaigns" in d["text"]
    assert d["stale_days"] >= 15  # the data ends 25 Oct; the digest says so
    assert any("Latest sales are from 25 Oct 2026" in n for n in d["notes"])
    assert d["watch"] is None  # no forecast has been built
    assert "Kulkarni" not in d["text"]  # the shop is named, with no stray demo text
    assert "R1" not in d["text"]  # no customer IDs ever appear in a digest


def test_weekly_digest_matches_hand_computed_numbers(client: TestClient, shop) -> None:
    d = client.get(url(shop, "/preview"), params={"kind": "weekly"}, headers=shop[0]).json()
    by = {h["key"]: h for h in d["headline"]}
    assert by["net_sales"]["value"] == "₹8,600"
    assert by["net_sales"]["change"] == "22.9"
    assert by["orders"]["value"] == "8"
    assert by["orders"]["change"] == "14.3"
    assert by["gross_margin"]["value"] == "39.7%"
    assert by["gross_margin"]["change"] == "-0.4"
    assert d["versus"] == "vs the week before"
    assert d["label"] == "19 Oct to 25 Oct 2026"
    assert d["text"].count("\n") < 20  # short enough for a phone message
    assert len(d["text"]) < 900


def test_html_is_escaped_and_carries_the_action(client: TestClient, shop) -> None:
    d = client.get(url(shop, "/preview"), headers=shop[0]).json()
    assert "Do this: Message 3 regular customers" in d["html"]
    assert "<script" not in d["html"]


def test_margin_is_hidden_when_costs_are_missing(client: TestClient, make_user) -> None:
    lines = shop_csv().strip().splitlines()
    i = lines[0].split(",").index("Cost")
    blank = [lines[0]] + [
        ",".join("" if j == i else v for j, v in enumerate(ln.split(","))) for ln in lines[1:]
    ]
    s = make_shop(client, make_user, "nc@shop.in", "\n".join(blank) + "\n")
    d = client.get(url(s, "/preview"), headers=s[0]).json()
    assert [h["key"] for h in d["headline"]] == ["net_sales", "orders", "aov"]
    assert any(a["kind"] == "add_costs" for a in [d["action"], *d["more_actions"]])
    assert any("Margin is hidden" in n for n in d["notes"])


def test_nothing_to_summarise_without_sales(client: TestClient, make_user) -> None:
    h = make_user("empty@shop.in", "E")
    ws = client.post("/api/v1/workspaces", json={"name": "Empty"}, headers=h).json()["id"]
    r = client.get(f"/api/v1/workspaces/{ws}/digests/preview", headers=h)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "no_sales"


def test_settings_validation_and_tenancy(client: TestClient, shop, make_user) -> None:
    h = shop[0]
    s = client.get(url(shop, "/settings"), headers=h).json()
    assert s["enabled"] is False
    assert s["email_configured"] is False
    ok = {
        "enabled": True,
        "frequency": "both",
        "send_hour": 8,
        "weekday": 0,
        "recipients": ["Owner@Shop.in", "owner@shop.in"],
    }
    r = client.put(url(shop, "/settings"), json=ok, headers=h).json()
    assert r["recipients"] == ["owner@shop.in"]  # lower-cased and de-duplicated
    for bad in (
        {**ok, "recipients": ["not-an-email"]},
        {**ok, "send_hour": 24},
        {**ok, "weekday": 7},
        {**ok, "frequency": "hourly"},
        {**ok, "recipients": [f"a{i}@x.in" for i in range(6)]},
    ):
        assert client.put(url(shop, "/settings"), json=bad, headers=h).status_code == 422
    stranger = make_user("st@x.in", "S")
    assert client.get(url(shop, "/settings"), headers=stranger).status_code == 404
    assert client.put(url(shop, "/settings"), json=ok, headers=stranger).status_code == 404


class FakeSMTP:
    sent: ClassVar[list] = []
    fail: ClassVar[bool] = False

    def __init__(self, host: str, port: int, timeout: int = 0) -> None:
        self.host = host

    def __enter__(self):
        if FakeSMTP.fail:
            raise OSError("connection refused")
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        pass

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.sent, FakeSMTP.fail = [], False
    monkeypatch.setattr(config.get_settings(), "smtp_host", "smtp.test")
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def set_recipients(client, shop, **kw):
    body = {
        "enabled": True,
        "frequency": "daily",
        "send_hour": 8,
        "weekday": 0,
        "recipients": ["owner@shop.in"],
        **kw,
    }
    assert client.put(url(shop, "/settings"), json=body, headers=shop[0]).status_code == 200


def test_send_now_needs_a_recipient(client: TestClient, shop) -> None:
    r = client.post(url(shop, "/send-now"), headers=shop[0])
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "no_recipients"


def test_send_now_without_smtp_is_stored_not_sent(client: TestClient, shop) -> None:
    set_recipients(client, shop)
    r = client.post(url(shop, "/send-now"), headers=shop[0]).json()
    assert r["status"] == "not_configured"
    assert r["sent_to"] == []
    assert "Sales: ₹1,400" in r["text"]


def test_send_now_emails_the_recipients(client: TestClient, shop, smtp) -> None:
    set_recipients(client, shop)
    r = client.post(url(shop, "/send-now"), params={"kind": "weekly"}, headers=shop[0]).json()
    assert r["status"] == "sent"
    assert r["sent_to"] == ["owner@shop.in"]
    msg = smtp.sent[0]
    assert msg["To"] == "owner@shop.in"
    assert "weekly summary" in msg["Subject"]
    assert msg.get_body(("plain",)).get_content().startswith("*")
    assert "Do this" in msg.get_body(("html",)).get_content()
    hist = client.get(url(shop, "/history"), headers=shop[0]).json()
    assert [h["status"] for h in hist] == ["sent"]


def test_a_failing_mail_server_is_reported_not_raised(client: TestClient, shop, smtp) -> None:
    smtp.fail = True
    set_recipients(client, shop)
    r = client.post(url(shop, "/send-now"), headers=shop[0]).json()
    assert r["status"] == "failed"
    assert "could not be sent" in r["error"]
    assert "refused" not in r["error"]  # internal detail is not shown to the user


# ---------------------------------------------------------------- the scheduled run


def test_run_due_sends_once_per_day_at_the_right_hour(
    client: TestClient, shop, smtp, db_session_factory
) -> None:
    set_recipients(client, shop, frequency="both", send_hour=8, weekday=0)
    mon_0900_ist = datetime(2026, 10, 26, 3, 30, tzinfo=UTC)  # a Monday, 09:00 in Kolkata
    with db_session_factory() as db:
        early = digest_delivery.run_due(db, datetime(2026, 10, 26, 1, 0, tzinfo=UTC))  # 06:30 IST
        assert early == []
        first = digest_delivery.run_due(db, mon_0900_ist)
        assert sorted(r["kind"] for r in first) == ["daily", "weekly"]  # Monday: both are due
        assert {r["status"] for r in first} == {"sent"}
        assert (
            digest_delivery.run_due(db, mon_0900_ist + timedelta(hours=1)) == []
        )  # not twice a day
        tue = digest_delivery.run_due(db, mon_0900_ist + timedelta(days=1))
        assert [r["kind"] for r in tue] == ["daily"]  # weekly only on the chosen weekday
    assert len(smtp.sent) == 3


def test_disabled_settings_are_never_run(
    client: TestClient, shop, smtp, db_session_factory
) -> None:
    set_recipients(client, shop, enabled=False)
    with db_session_factory() as db:
        assert digest_delivery.run_due(db, datetime(2026, 10, 26, 5, 0, tzinfo=UTC)) == []
    assert smtp.sent == []
