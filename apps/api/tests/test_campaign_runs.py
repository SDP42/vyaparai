# ruff: noqa: E501
"""Consent, launching, the outbox, opt-outs, the daily cap, and the measured result with honest intervals."""

import random
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.campaign import Campaign, CampaignRecipient
from app.services import uplift
from tests.test_intelligence_api import CUSTOMERS_CSV, make_shop
from tests.test_team import _join

CONTACTS = "Customer,Phone,Consent,Source\nD,9876543210,yes,asked at the counter\nF,9123456780,yes,WhatsApp opt-in\nA,9000000001,no,refused\nB,,yes,counter\n"


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "run@shop.in", CUSTOMERS_CSV)


def base(shop) -> str:
    return f"/api/v1/workspaces/{shop[1]}/campaigns"


def _contacts(client, shop, text: str = CONTACTS):
    return client.post(
        f"{base(shop)}/contacts/import", files={"file": ("c.csv", text.encode())}, headers=shop[0]
    )


def _launch(client, shop, **kw):
    body = {"name": "Welcome back", "segment": "New", "holdout_pct": 0, "language": "en", **kw}
    return client.post(f"{base(shop)}/runs", json=body, headers=shop[0])


# ------------------------------------------------------------------ statistics


def test_wilson_and_newcombe_behave() -> None:
    lo, hi = uplift.wilson(20, 100)
    assert 0.13 < lo < 0.20 < hi < 0.29
    d, a, b = uplift.newcombe_diff(30, 100, 20, 100)
    assert round(d, 2) == 0.10
    assert a < 0 < b  # 100 per group cannot prove a 10-point lift
    _, a2, _ = uplift.newcombe_diff(300, 1000, 200, 1000)
    assert a2 > 0  # 1000 per group can


def test_a_real_effect_is_found_and_no_effect_is_inconclusive() -> None:
    rng = random.Random(3)  # noqa: S311  (test data, not security)

    def group(n: int, rate: float, spend: float) -> list[uplift.Person]:
        return [
            uplift.Person(
                b := rng.random() < rate,
                spend * rng.uniform(0.5, 1.5) if b else 0.0,
                0.3 * spend if b else 0.0,
            )
            for _ in range(n)
        ]

    win = uplift.compare(group(600, 0.30, 400), group(600, 0.20, 400))
    assert win["purchase_rate"]["verdict"] == "positive"
    assert win["profit"]["verdict"] == "positive"
    assert win["revenue"]["incremental_total"] > 0
    nothing = uplift.compare(group(600, 0.25, 400), group(600, 0.25, 400))
    assert nothing["purchase_rate"]["verdict"] == "inconclusive"
    worse = uplift.compare(group(600, 0.15, 400), group(600, 0.30, 400))
    assert worse["purchase_rate"]["verdict"] == "negative"


def test_small_groups_and_missing_holdout_are_flagged() -> None:
    few = [uplift.Person(True, 100, 40)] * 5
    r = uplift.compare(few, [uplift.Person(False, 0, 0)] * 4)
    assert any("Only 5 messaged and 4 held back" in w for w in r["warnings"])
    none = uplift.compare(few, [])
    assert any("no holdout" in w for w in none["warnings"])
    assert none["purchase_rate"]["verdict"] == "inconclusive"


def test_bootstrap_is_repeatable_and_sample_size_advice_grows_for_small_lifts() -> None:
    a, b = [1.0, 2.0, 3.0, 10.0], [1.0, 1.0, 2.0, 2.0]
    assert uplift.bootstrap_diff(a, b) == uplift.bootstrap_diff(a, b)
    assert uplift.needed_per_group(0.2, 2.0) > uplift.needed_per_group(0.2, 5.0)


# ------------------------------------------------------------------ consent


def test_import_records_consent_and_masks_phones(client: TestClient, shop) -> None:
    r = _contacts(client, shop).json()
    assert r["saved"] == 4
    s = client.get(f"{base(shop)}/contacts/summary", headers=shop[0]).json()
    assert (s["granted"], s["denied"], s["reachable"], s["no_phone"], s["opted_out"]) == (
        3,
        1,
        2,
        1,
        1,
    )
    rows = client.get(f"{base(shop)}/contacts", headers=shop[0]).json()
    assert all(x["phone"] is None or x["phone"].startswith("•••• ") for x in rows)
    assert "9876543210" not in str(rows)


def test_an_opt_out_sticks_until_the_customer_agrees_again_with_a_source(
    client: TestClient, shop
) -> None:
    _contacts(client, shop)
    b = base(shop)
    h = shop[0]
    assert (
        client.post(f"{b}/contacts/opt-out", json={"customer_key": "D"}, headers=h).json()[
            "opted_out"
        ]
        == 1
    )
    assert client.get(f"{b}/contacts/summary", headers=h).json()["reachable"] == 1
    assert (
        client.put(
            f"{b}/contacts", json={"customer_key": "D", "consent": "granted"}, headers=h
        ).status_code
        == 400
    )
    ok = client.put(
        f"{b}/contacts",
        json={"customer_key": "D", "consent": "granted", "source": "asked again at the counter"},
        headers=h,
    )
    assert ok.status_code == 200
    assert client.get(f"{b}/contacts/summary", headers=h).json()["reachable"] == 2
    assert (
        client.post(f"{b}/contacts/opt-out", json={"phone": "98765 43210"}, headers=h).json()[
            "opted_out"
        ]
        == 1
    )  # by phone


# ------------------------------------------------------------------ launch, outbox, cap


def test_nobody_is_messaged_without_recorded_consent(client: TestClient, shop) -> None:
    r = _launch(client, shop)
    assert r.status_code == 400
    assert "consent" in r.json()["error"]["message"].lower()


def test_launch_uses_only_consented_customers_and_builds_whatsapp_links(
    client: TestClient, shop
) -> None:
    _contacts(client, shop)
    c = _launch(client, shop).json()
    assert c["counts"]["eligible"] == 2  # D and F are the "New" customers with consent and a phone
    assert c["counts"]["treatment"] == 2
    ob = client.get(f"{base(shop)}/runs/{c['id']}/outbox", headers=shop[0]).json()
    assert {i["customer_key"] for i in ob["items"]} == {"D", "F"}
    first = ob["items"][0]
    assert first["whatsapp"].startswith("https://wa.me/91")
    assert "STOP" in first["message"] or "stop" in first["message"].lower()
    assert first["phone"].startswith("•••• ")
    assert ob["daily_cap"] == get_settings().campaign_daily_cap


def test_an_opt_out_after_launch_removes_the_person_from_the_outbox(
    client: TestClient, shop
) -> None:
    _contacts(client, shop)
    c = _launch(client, shop).json()
    client.post(f"{base(shop)}/contacts/opt-out", json={"customer_key": "F"}, headers=shop[0])
    ob = client.get(f"{base(shop)}/runs/{c['id']}/outbox", headers=shop[0]).json()
    assert [i["customer_key"] for i in ob["items"]] == ["D"]
    sent = client.post(
        f"{base(shop)}/runs/{c['id']}/mark-sent",
        json={"ids": [i["id"] for i in ob["items"]]},
        headers=shop[0],
    ).json()
    assert sent["marked"] == 1
    run = client.get(f"{base(shop)}/runs/{c['id']}", headers=shop[0]).json()
    assert run["started_on"]
    assert run["status"] == "sending"


def test_the_daily_cap_limits_how_many_can_be_marked_sent(
    client: TestClient, shop, monkeypatch
) -> None:
    _contacts(client, shop)
    c = _launch(client, shop).json()
    monkeypatch.setattr(get_settings(), "campaign_daily_cap", 1)
    ob = client.get(f"{base(shop)}/runs/{c['id']}/outbox", headers=shop[0]).json()
    ids = [i["id"] for i in ob["items"]]
    assert (
        client.post(
            f"{base(shop)}/runs/{c['id']}/mark-sent", json={"ids": ids}, headers=shop[0]
        ).json()["marked"]
        == 1
    )
    assert (
        client.post(
            f"{base(shop)}/runs/{c['id']}/mark-sent", json={"ids": ids}, headers=shop[0]
        ).status_code
        == 409
    )


def test_holdout_is_drawn_from_the_consented_group_and_never_messaged(
    client: TestClient, shop, db_session_factory: sessionmaker[Session]
) -> None:
    keys = "Customer,Phone,Consent\n" + "\n".join(
        f"{k},98765432{i}0,yes" for i, k in enumerate("ABCDEF")
    )
    _contacts(client, shop, keys)
    c = _launch(client, shop, segment="New", holdout_pct=50).json()
    with db_session_factory() as db:
        recs = (
            db.query(CampaignRecipient)
            .filter(CampaignRecipient.campaign_id == uuid.UUID(c["id"]))
            .all()
        )
    groups = {r.customer_key: r.group for r in recs}
    assert set(groups) == {"D", "F"}
    ob = client.get(f"{base(shop)}/runs/{c['id']}/outbox", headers=shop[0]).json()
    assert all(groups[i["customer_key"]] == "treatment" for i in ob["items"])


# ------------------------------------------------------------------ result on the fixture


def test_results_compare_messaged_and_held_back_customers_on_real_orders(
    client: TestClient, shop, db_session_factory: sessionmaker[Session]
) -> None:
    ws = uuid.UUID(shop[1])
    with db_session_factory() as db:
        camp = Campaign(
            workspace_id=ws,
            name="t",
            segment="New",
            status="sending",
            params={},
            window_days=14,
            holdout_pct=50,
            started_on=date(2026, 10, 26),
            counts={},
        )
        db.add(camp)
        db.flush()
        for key, group, status in (
            ("B", "treatment", "sent"),
            ("F", "treatment", "sent"),
            ("A", "holdout", "pending"),
            ("D", "holdout", "pending"),
            ("E", "treatment", "pending"),
        ):
            db.add(
                CampaignRecipient(
                    workspace_id=ws,
                    campaign_id=camp.id,
                    customer_key=key,
                    group=group,
                    message="m",
                    status=status,
                )
            )
        db.commit()
        cid = str(camp.id)
    r = client.get(f"{base(shop)}/runs/{cid}/results", headers=shop[0]).json()
    assert r["ready"] is True
    assert r["treated"]["customers"] == 2  # only messages actually sent count
    assert r["not_sent_yet"] == 1
    # B bought 100 on 30 Oct and F 80 on 31 Oct (cost 60%); in the holdout A bought 200 on 28 Oct, D bought before the window
    assert r["treated"]["bought"] == 2
    assert r["treated"]["revenue_per_customer"] == 90.0
    assert round(r["treated"]["profit_per_customer"], 1) == 36.0
    assert r["holdout"]["customers"] == 2
    assert r["holdout"]["bought"] == 1
    assert r["holdout"]["revenue_per_customer"] == 100.0
    assert r["purchase_rate"]["verdict"] == "inconclusive"
    assert any("Only 2 messaged" in w for w in r["warnings"])
    assert "fair comparison" in r["caveat"]


def test_results_say_so_before_anything_is_sent(client: TestClient, shop) -> None:
    _contacts(client, shop)
    c = _launch(client, shop).json()
    r = client.get(f"{base(shop)}/runs/{c['id']}/results", headers=shop[0]).json()
    assert r["ready"] is False
    assert "Nothing has been sent" in r["message"]


def test_permissions_and_tenancy(client: TestClient, shop, make_user) -> None:
    h, ws = shop
    _contacts(client, shop)
    c = _launch(client, shop).json()
    analyst, viewer, stranger = (
        make_user("an@shop.in"),
        make_user("vi@shop.in"),
        make_user("st@shop.in"),
    )
    _join(client, ws, h, analyst, "analyst")
    _join(client, ws, h, viewer, "viewer")
    b = base(shop)
    assert client.get(f"{b}/contacts/summary", headers=viewer).status_code == 200
    assert client.get(f"{b}/contacts", headers=viewer).status_code == 403
    assert (
        client.put(
            f"{b}/contacts",
            json={"customer_key": "Z", "consent": "granted", "source": "x"},
            headers=analyst,
        ).status_code
        == 200
    )
    assert (
        client.post(f"{b}/runs", json={"name": "x", "segment": "New"}, headers=analyst).status_code
        == 403
    )  # sending is an admin decision
    assert client.get(f"{b}/runs/{c['id']}/outbox", headers=analyst).status_code == 403
    assert client.get(f"{b}/runs/{c['id']}", headers=stranger).status_code == 404
